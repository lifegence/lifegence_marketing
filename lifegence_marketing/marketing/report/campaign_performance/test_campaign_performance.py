# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""The four reports on one small data set: April 2026, campaign lm-test-expo on Meta (and an unmatched brand campaign)."""

import frappe
from frappe.tests import IntegrationTestCase

from lifegence_marketing.marketing.doctype.marketing_campaign.marketing_campaign import on_ringi_update
from lifegence_marketing.marketing.doctype.marketing_campaign.test_marketing_campaign import make_campaign
from lifegence_marketing.marketing.doctype.marketing_import.test_marketing_import import (
	META_CSV,
	make_account,
	run_import,
)
from lifegence_marketing.marketing.report.ad_spend_reconciliation import ad_spend_reconciliation
from lifegence_marketing.marketing.report.budget_vs_actual import budget_vs_actual
from lifegence_marketing.marketing.report.campaign_performance import campaign_performance
from lifegence_marketing.marketing.report.channel_summary import channel_summary

APRIL = {"from_date": "2026-04-01", "to_date": "2026-04-30"}


def attributed_lead(n, campaign="lm-test-expo", source="meta"):
	"""An ERPNext-style lead record with its attribution, recorded in April."""
	name = f"LM-TEST-LEAD-{n}"
	frappe.get_doc(
		{
			"doctype": "Marketing Attribution",
			"reference_doctype": "Lead" if "erpnext" in frappe.get_installed_apps() else "User",
			"reference_name": name,
			"last_source": source,
			"last_campaign": campaign,
			"last_campaign_link": campaign,
			"first_source": source,
			"first_campaign_link": campaign,
			"recorded_on": "2026-04-05 10:00:00",
		}
	).db_insert()
	return name


def raw(doctype, **values):
	doc = frappe.new_doc(doctype)
	doc.update(values)
	doc.name = values.get("name") or frappe.generate_hash(length=10)
	doc.db_insert()  # only the columns the reports read
	return doc


def by(rows, **kw):
	return next(r for r in rows if all(r.get(k) == v for k, v in kw.items()))


class TestReports(IntegrationTestCase):
	def setUp(self):
		self.campaign = make_campaign(
			budgets=[
				{"channel": "Meta", "month": "2026-04-01", "amount": 100000},
				{"channel": "Google", "month": "2026-04-01", "amount": 50000},
			]
		)
		self.account = make_account()
		run_import(
			self.account, META_CSV
		)  # lm-test-expo: 5,000 + 3,000 on 04-01; brand_search: 1,000 on 04-02
		self.leads = [attributed_lead(1), attributed_lead(2)]
		self.erpnext = "erpnext" in frappe.get_installed_apps()
		if self.erpnext:
			raw(
				"Opportunity",
				opportunity_from="Lead",
				party_name=self.leads[0],
				status="Converted",
				base_opportunity_amount=300000,
				docstatus=0,
			)
			raw(
				"Sales Invoice",
				docstatus=1,
				posting_date="2026-04-20",
				utm_campaign="lm-test-expo",
				utm_source="meta",
				base_net_total=200000,
			)

	def tearDown(self):
		frappe.db.rollback()

	def test_campaign_performance_by_campaign(self):
		_cols, rows = campaign_performance.execute({**APRIL, "group_by": "Campaign"})
		r = by(rows, campaign="lm-test-expo")
		self.assertEqual((r["budget"], r["cost"], r["impressions"], r["clicks"]), (150000, 8000, 2034, 65))
		self.assertEqual(r["leads"], 2)
		self.assertEqual(r["cpa"], 4000)
		if self.erpnext:
			self.assertEqual((r["deals"], r["won"], r["won_amount"]), (1, 1, 300000))
			self.assertEqual(r["revenue"], 200000)
			self.assertEqual(r["roas"], 25)
		self.assertEqual(by(rows, campaign=None)["cost"], 1000)  # the unmatched campaign

	def test_campaign_performance_by_channel_and_filters(self):
		_cols, rows = campaign_performance.execute({**APRIL, "group_by": "Channel"})
		meta = by(rows, channel="Meta")
		self.assertEqual((meta["cost"], meta["leads"]), (9000, 2))
		_cols, rows = campaign_performance.execute(
			{**APRIL, "group_by": "Campaign and Channel", "campaign": "lm-test-expo"}
		)
		self.assertEqual(
			{(r["campaign"], r["channel"]) for r in rows},
			{("lm-test-expo", "Meta"), ("lm-test-expo", "Google")},
		)
		_cols, rows = campaign_performance.execute({"from_date": "2026-05-01", "to_date": "2026-05-31"})
		self.assertEqual(rows, [])

	def test_budget_vs_actual(self):
		_cols, rows = budget_vs_actual.execute(APRIL)
		meta = by(rows, campaign="lm-test-expo", channel="Meta")
		self.assertEqual(
			(meta["budget"], meta["cost"], meta["used"], meta["remaining"]), (100000, 8000, 8, 92000)
		)
		self.assertEqual(meta["forecast"], 8000)  # a past month is what was spent
		google = by(rows, campaign="lm-test-expo", channel="Google")
		self.assertEqual((google["budget"], google["cost"]), (50000, 0))

	def test_forecast_of_the_current_month(self):
		self.assertEqual(budget_vs_actual.forecast("2026-04-01", 10000, today="2026-04-10"), 30000)
		self.assertEqual(budget_vs_actual.forecast("2026-03-01", 10000, today="2026-04-10"), 10000)

	def test_channel_summary(self):
		_cols, rows, _msg, chart = channel_summary.execute(APRIL)
		meta = by(rows, channel="Meta", month="2026-04-01")
		self.assertEqual((meta["cost"], meta["leads"], meta["cpa"]), (9000, 2, 4500))
		if self.erpnext:
			self.assertEqual(meta["revenue"], 200000)
		self.assertEqual(chart["data"]["labels"], ["2026-04-01"])

	def test_ad_spend_reconciliation(self):
		result = ad_spend_reconciliation.execute(APRIL)
		if not self.erpnext:
			self.assertEqual(result[1], [])
			return
		pi = raw("Purchase Invoice", docstatus=1, posting_date="2026-04-20")
		raw(
			"Purchase Invoice Item",
			parent=pi.name,
			parenttype="Purchase Invoice",
			parentfield="items",
			marketing_campaign="lm-test-expo",
			marketing_channel="Meta",
			base_net_amount=7000,
		)
		_cols, rows = ad_spend_reconciliation.execute(APRIL)[:2]
		r = by(rows, campaign="lm-test-expo", channel="Meta")
		self.assertEqual((r["media_cost"], r["invoiced"], r["difference"]), (8000, 7000, 1000))

	def test_decided_ringi_notifies_the_owner(self):
		self.campaign.db_set({"status": "Pending Approval", "campaign_owner": "Administrator"})

		class Ringi(frappe._dict):
			def get_doc_before_save(self):
				return frappe._dict(status="In Approval")

		before = frappe.db.count("Notification Log", {"document_name": self.campaign.name})
		on_ringi_update(
			Ringi(reference_doctype="Marketing Campaign", reference_name=self.campaign.name, status="Decided")
		)
		self.assertEqual(
			frappe.db.count("Notification Log", {"document_name": self.campaign.name}), before + 1
		)

	def test_frappe_crm_deals(self):
		if "crm" not in frappe.get_installed_apps():
			self.skipTest("Frappe CRM is not installed")
		won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name")[0]
		frappe.local.request = None
		lead = frappe.get_doc(
			{"doctype": "CRM Lead", "first_name": "LM Deal", "email": "lm-deal@example.com"}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Marketing Attribution",
				"reference_doctype": "CRM Lead",
				"reference_name": lead.name,
				"last_source": "meta",
				"last_campaign_link": "lm-test-expo",
				"recorded_on": "2026-04-06 09:00:00",
			}
		).insert()
		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"lead": lead.name,
				"first_name": "LM Deal",
				"email": "lm-deal@example.com",
				"status": won,
				"deal_value": 500000,
			}
		)
		deal.insert(ignore_mandatory=True)
		_cols, rows = campaign_performance.execute({**APRIL, "group_by": "Campaign"})
		r = by(rows, campaign="lm-test-expo")
		self.assertEqual(r["leads"], 3)
		self.assertGreaterEqual(r["won"], 1)
		self.assertGreaterEqual(r["won_amount"], 500000)
