# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from lifegence_marketing.marketing.doctype.marketing_campaign.marketing_campaign import normalize_code

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
]

CODE = "lm-test-expo"


def make_campaign(code=CODE, **kw):
	if frappe.db.exists("Marketing Campaign", normalize_code(code)):
		frappe.delete_doc("Marketing Campaign", normalize_code(code), force=True)
	return frappe.get_doc(
		{
			"doctype": "Marketing Campaign",
			"campaign_name": kw.pop("campaign_name", "展示会 2026 春"),
			"campaign_code": code,
			"from_date": "2026-04-01",
			"to_date": "2026-06-30",
			"currency": "JPY",
			**kw,
		}
	).insert()


class TestMarketingCampaign(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_code_creates_the_utm_campaign(self):
		c = make_campaign(code=" LM Test  Expo ")
		self.assertEqual(c.name, CODE)
		self.assertEqual(c.utm_campaign, CODE)
		self.assertEqual(frappe.db.get_value("UTM Campaign", CODE, "slug"), CODE)

	def test_invalid_code(self):
		with self.assertRaises(frappe.ValidationError):
			make_campaign(code="展示会")

	def test_budget_months_and_total(self):
		c = make_campaign(
			budgets=[
				{"channel": "Meta", "month": "2026-04-15", "amount": 300000},
				{"channel": "Google", "month": "2026-04-01", "amount": 200000},
				{"channel": "Meta", "month": "2026-05-20", "amount": 100000},
			]
		)
		self.assertEqual(str(c.budgets[0].month), "2026-04-01")
		self.assertEqual(c.total_budget, 600000)
		c.append("budgets", {"channel": "Meta", "month": "2026-04-30", "amount": 1})
		with self.assertRaises(frappe.ValidationError):
			c.save()

	def test_dates(self):
		with self.assertRaises(frappe.ValidationError):
			make_campaign(from_date="2026-06-30", to_date="2026-04-01")

	def test_activation_needs_a_decided_ringi_when_required(self):
		c = make_campaign()
		if "japan_workplace" not in frappe.get_installed_apps() or not frappe.db.table_exists("Ringi"):
			c.status = "Active"
			c.save()  # no ringi needed without japan_workplace
			return
		frappe.db.set_single_value("Marketing Settings", "require_ringi", 1)
		frappe.db.set_single_value("Marketing Settings", "ringi_type", None)
		c.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			c.save()
		frappe.db.set_single_value("Marketing Settings", "require_ringi", 0)
		c.reload()
		c.status = "Active"
		c.save()
		self.assertEqual(c.status, "Active")
