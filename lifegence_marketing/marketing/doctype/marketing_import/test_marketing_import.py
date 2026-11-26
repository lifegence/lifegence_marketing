# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from lifegence_marketing.marketing.doctype.marketing_campaign.test_marketing_campaign import make_campaign

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"UTM Campaign",
	"UTM Source",
	"UTM Medium",
	"Currency",
	"User",
	"Company",
	"Cost Center",
	"Project",
	"Ringi Type",
	"Marketing Campaign",
	"Supplier",
	"Connected App",
	"Marketing Ad Account",
	"Marketing Import Profile",
	"Marketing Channel",
]

META_CSV = """Reporting starts,Campaign name,Ad set name,Ad name,Platform,Impressions,Reach,Link clicks,Amount spent (JPY),Results
2026-04-01,lm-test-expo_retargeting,Visitors 30d,Banner A,facebook,"1,234",900,40,"5,000",3
2026-04-01,lm-test-expo_retargeting,Visitors 30d,Banner A,instagram,800,700,25,"3,000",1
2026-04-02,brand_search,Brand,Text 1,facebook,500,400,10,"1,000",0
Total,,,,,"2,534","2,000",75,"9,000",4
"""

JA_CSV = """日,キャンペーン名,広告グループ名,インプレッション数,クリック数,費用,コンバージョン数
2026/04/01,lm-test-expo_検索,展示会 キーワード,"10,000",300,"\uffe512,000",5
不正な日付,lm-test-expo_検索,展示会 キーワード,1,1,1,0
合計,,,"10,001",301,"12,001",5
"""


def make_account():
	name = frappe.db.get_value("Marketing Ad Account", {"channel": "Meta", "external_id": "lm-test-acc"})
	if name:
		return frappe.get_doc("Marketing Ad Account", name)
	return frappe.get_doc(
		{
			"doctype": "Marketing Ad Account",
			"account_name": "LM Test",
			"channel": "Meta",
			"external_id": "lm-test-acc",
			"currency": "JPY",
		}
	).insert()


def run_import(account, content, file_name="perf.csv", profile=None):
	f = frappe.get_doc(
		{"doctype": "File", "file_name": file_name, "content": content, "is_private": 1}
	).insert(ignore_permissions=True)
	imp = frappe.get_doc(
		{"doctype": "Marketing Import", "ad_account": account.name, "file": f.file_url, "profile": profile}
	).insert()
	imp.run()
	imp.reload()
	return imp


def perf(account, **filters):
	return frappe.get_all(
		"Marketing Performance",
		filters={"ad_account": account.name, **filters},
		fields=[
			"date",
			"placement",
			"impressions",
			"reach",
			"clicks",
			"cost",
			"conversions",
			"marketing_campaign",
			"ad_object",
		],
		order_by="date, placement",
	)


class TestMarketingImport(IntegrationTestCase):
	def setUp(self):
		self.campaign = make_campaign()
		self.account = make_account()

	def tearDown(self):
		frappe.db.rollback()

	def test_meta_export_in_english(self):
		imp = run_import(self.account, META_CSV)
		self.assertEqual(imp.status, "Done", imp.messages)
		self.assertEqual(imp.rows_imported, 3)  # the total row is skipped
		self.assertEqual((str(imp.date_from), str(imp.date_to)), ("2026-04-01", "2026-04-02"))
		rows = perf(self.account)
		self.assertEqual(
			[(str(r.date), r.placement) for r in rows],
			[("2026-04-01", "facebook"), ("2026-04-01", "instagram"), ("2026-04-02", "facebook")],
		)
		self.assertEqual(rows[0].impressions, 1234)
		self.assertEqual(rows[0].cost, 5000)
		self.assertEqual(rows[0].conversions, 3)
		self.assertEqual(rows[0].marketing_campaign, "lm-test-expo")  # campaign code before the separator
		self.assertIsNone(rows[2].marketing_campaign)  # brand_search matches no campaign
		ad = frappe.get_doc("Marketing Ad Object", rows[0].ad_object)
		group = frappe.get_doc("Marketing Ad Object", ad.parent_object)
		top = frappe.get_doc("Marketing Ad Object", group.parent_object)
		self.assertEqual((ad.object_type, group.object_type, top.object_type), ("Ad", "Ad Group", "Campaign"))
		self.assertEqual(top.external_id, "name:lm-test-expo_retargeting")
		self.assertEqual(ad.marketing_campaign, "lm-test-expo")  # inherited

	def test_importing_again_replaces(self):
		run_import(self.account, META_CSV)
		run_import(self.account, META_CSV.replace('"5,000"', '"6,000"'))
		rows = perf(self.account)
		self.assertEqual(len(rows), 3)
		self.assertEqual(rows[0].cost, 6000)

	def test_japanese_export_in_shift_jis(self):
		imp = run_import(self.account, JA_CSV.encode("cp932"), "ja.csv")
		self.assertEqual(imp.status, "Done", imp.messages)
		self.assertEqual(imp.rows_imported, 1)
		self.assertEqual(imp.rows_skipped, 1)
		self.assertIn("不正な日付", imp.messages)
		row = perf(self.account)[0]
		self.assertEqual((row.impressions, row.clicks, row.cost, row.conversions), (10000, 300, 12000, 5))
		self.assertEqual(row.marketing_campaign, "lm-test-expo")

	def test_matching_by_hand_applies_below(self):
		run_import(self.account, META_CSV)
		other = make_campaign(code="lm-test-brand", campaign_name="ブランド")
		top = frappe.get_doc(
			"Marketing Ad Object", {"ad_account": self.account.name, "external_id": "name:brand_search"}
		)
		top.marketing_campaign = other.name
		top.save()
		self.assertTrue(top.mapped_manually)
		self.assertEqual(
			[r.marketing_campaign for r in perf(self.account, date="2026-04-02")], ["lm-test-brand"]
		)
		run_import(self.account, META_CSV)  # importing again keeps the match
		self.assertEqual(
			[r.marketing_campaign for r in perf(self.account, date="2026-04-02")], ["lm-test-brand"]
		)

	def test_missing_columns_fail(self):
		imp = run_import(self.account, "Name,Value\na,1\n")
		self.assertEqual(imp.status, "Failed")
		self.assertIn("date", imp.messages)

	def test_profile_names_other_columns(self):
		if frappe.db.exists("Marketing Import Profile", "LM Test Profile"):
			frappe.delete_doc("Marketing Import Profile", "LM Test Profile", force=True)
		frappe.get_doc(
			{
				"doctype": "Marketing Import Profile",
				"profile_name": "LM Test Profile",
				"skip_rows": 2,
				"columns": [
					{"target": "cost", "source_column": "Spend total"},
					{"target": "date", "source_column": "Day of report"},
				],
			}
		).insert()
		csv = "Performance report\nApril 2026\nDay of report,Campaign,Spend total,Clicks\n2026-04-03,lm-test-expo_x,700,7\n"
		imp = run_import(self.account, csv, profile="LM Test Profile")
		self.assertEqual(imp.status, "Done", imp.messages)
		row = perf(self.account)[0]
		self.assertEqual((str(row.date), row.cost, row.clicks), ("2026-04-03", 700, 7))
