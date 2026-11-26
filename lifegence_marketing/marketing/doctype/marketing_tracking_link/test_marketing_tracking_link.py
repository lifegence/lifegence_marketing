# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

from urllib.parse import parse_qs, urlsplit

import frappe
from frappe.tests import IntegrationTestCase

from lifegence_marketing.marketing.doctype.marketing_campaign.test_marketing_campaign import make_campaign
from lifegence_marketing.marketing.doctype.marketing_tracking_link.marketing_tracking_link import resolve

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
	"Marketing Creative",
]


class TestMarketingTrackingLink(IntegrationTestCase):
	def setUp(self):
		self.campaign = make_campaign()

	def tearDown(self):
		frappe.db.rollback()

	def make(self, **kw):
		return frappe.get_doc(
			{
				"doctype": "Marketing Tracking Link",
				"campaign": self.campaign.name,
				"channel": "Meta",
				"base_url": "https://example.com/lp?ref=a#form",
				**kw,
			}
		).insert()

	def test_url_with_utm(self):
		link = self.make(utm_content="Banner A")
		parts = urlsplit(link.full_url)
		q = parse_qs(parts.query)
		self.assertEqual(q["utm_source"], ["meta"])
		self.assertEqual(q["utm_medium"], ["paid_social"])
		self.assertEqual(q["utm_campaign"], ["lm-test-expo"])
		self.assertEqual(q["utm_content"], ["banner_a"])
		self.assertEqual(q["ref"], ["a"])  # the existing query is kept
		self.assertEqual(parts.fragment, "form")

	def test_existing_utm_is_replaced(self):
		link = self.make(base_url="https://example.com/?utm_source=old&utm_campaign=old")
		q = parse_qs(urlsplit(link.full_url).query)
		self.assertEqual(q["utm_source"], ["meta"])
		self.assertEqual(q["utm_campaign"], ["lm-test-expo"])

	def test_short_url_and_qr(self):
		link = self.make()
		link.reload()
		self.assertTrue(link.short_url.endswith(f"/m/{link.name}"))
		self.assertTrue(link.qr_code.endswith(".svg"))

	def test_resolve_counts_clicks(self):
		link = self.make()
		self.assertEqual(resolve(link.name), link.full_url)
		self.assertEqual(resolve(link.name), link.full_url)
		self.assertEqual(frappe.db.get_value("Marketing Tracking Link", link.name, "clicks"), 2)
		link.db_set("disabled", 1)
		self.assertIsNone(resolve(link.name))
		self.assertIsNone(resolve("no-such-code"))

	def test_rejects_other_schemes(self):
		with self.assertRaises(frappe.ValidationError):
			self.make(base_url="javascript:alert(1)")
