# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

from http.cookies import SimpleCookie

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from lifegence_marketing.attribution import COOKIE, after_request, decode, encode
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
	"Lead",
	"CRM Lead",
	"CRM Deal",
	"Territory",
	"Industry Type",
	"Market Segment",
	"Lead Source",
]


def request(path="/lp", query="", cookie=None, method="GET"):
	headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
	return Request(
		EnvironBuilder(path=path, query_string=query, headers=headers, method=method).get_environ()
	)


def cookie_of(response):
	jar = SimpleCookie()
	for header in response.headers.getlist("Set-Cookie"):
		jar.load(header)
	return jar[COOKIE].value if COOKIE in jar else None


def visit(path="/lp", query="", cookie=None, **kw):
	response = Response()
	after_request(response, request(path, query, cookie, **kw))
	return cookie_of(response)


class TestAttributionCookie(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_document_cache("Marketing Settings", "Marketing Settings")

	def test_first_touch_is_kept_and_last_touch_replaced(self):
		c1 = visit(query="utm_source=meta&utm_medium=paid_social&utm_campaign=lm-test-expo&fbclid=abc")
		data = decode(c1)
		self.assertEqual(data["f"]["source"], "meta")
		self.assertEqual(data["f"]["landing"], "/lp")
		self.assertEqual(data["c"], {"fbclid": "abc"})
		c2 = visit(path="/pricing", query="utm_source=google&utm_campaign=brand&gclid=xyz", cookie=c1)
		data = decode(c2)
		self.assertEqual(data["f"]["source"], "meta")
		self.assertEqual(data["l"]["source"], "google")
		self.assertEqual(data["l"]["landing"], "/pricing")
		self.assertEqual(data["c"], {"fbclid": "abc", "gclid": "xyz"})

	def test_nothing_without_parameters_or_outside_the_website(self):
		self.assertIsNone(visit(query=""))
		self.assertIsNone(visit(query="page=2"))
		self.assertIsNone(visit(path="/api/method/ping", query="utm_source=meta"))
		self.assertIsNone(visit(path="/app/lead", query="utm_source=meta"))
		self.assertIsNone(visit(query="utm_source=meta", method="POST"))

	def test_consent(self):
		frappe.db.set_single_value(
			"Marketing Settings", {"cookie_consent_required": 1, "consent_cookie_name": "cookie_ok"}
		)
		frappe.clear_document_cache("Marketing Settings", "Marketing Settings")
		self.assertIsNone(visit(query="utm_source=meta"))
		response = Response()
		req = Request(
			EnvironBuilder(
				path="/lp", query_string="utm_source=meta", headers={"Cookie": "cookie_ok=1"}
			).get_environ()
		)
		after_request(response, req)
		self.assertTrue(cookie_of(response))

	def test_broken_cookie_is_ignored(self):
		self.assertEqual(decode("not-base64!!"), {})
		self.assertEqual(decode(encode([1, 2])), {})


class TestAttributionOnLeads(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.campaign = make_campaign()  # UTM Campaign lm-test-expo
		frappe.db.commit()

	def tearDown(self):
		frappe.local.request = None
		frappe.db.rollback()

	def with_cookie(self, first, last=None, clicks=None):
		data = {"f": first, "l": last or first, "c": clicks or {}}
		frappe.local.request = request(cookie=encode(data))

	def test_erpnext_lead_gets_known_values_and_attribution(self):
		if "erpnext" not in frappe.get_installed_apps():
			self.skipTest("ERPNext is not installed")
		self.with_cookie(
			{
				"source": "google",
				"medium": "cpc",
				"campaign": "brand-unknown",
				"landing": "/",
				"at": 1790000000,
			},
			{
				"source": "meta",
				"medium": "paid_social",
				"campaign": "lm-test-expo",
				"content": "banner_a",
				"landing": "/lp",
				"at": 1790100000,
			},
			{"fbclid": "abc"},
		)
		lead = frappe.get_doc(
			{"doctype": "Lead", "first_name": "LM Test", "email_id": "lm-test-lead@example.com"}
		).insert()
		self.assertEqual(lead.utm_source, "meta")
		self.assertEqual(lead.utm_medium, "paid_social")
		self.assertEqual(lead.utm_campaign, "lm-test-expo")
		a = frappe.get_doc(
			"Marketing Attribution", {"reference_doctype": "Lead", "reference_name": lead.name}
		)
		self.assertEqual(a.first_source, "google")
		self.assertEqual(a.first_campaign, "brand-unknown")  # kept as raw text
		self.assertIsNone(a.first_campaign_link)
		self.assertEqual(a.last_campaign_link, "lm-test-expo")
		self.assertEqual(a.last_content, "banner_a")
		self.assertIn("fbclid", a.click_ids)
		self.assertTrue(a.last_at)

	def test_unknown_values_do_not_fill_the_lead(self):
		if "erpnext" not in frappe.get_installed_apps():
			self.skipTest("ERPNext is not installed")
		self.with_cookie({"source": "spam-source", "campaign": "spam", "landing": "/"})
		lead = frappe.get_doc(
			{"doctype": "Lead", "first_name": "LM Test 2", "email_id": "lm-test-lead2@example.com"}
		).insert()
		self.assertFalse(lead.utm_source)
		self.assertFalse(lead.utm_campaign)
		self.assertFalse(frappe.db.exists("UTM Source", "spam-source"))

	def test_no_cookie_no_attribution(self):
		if "erpnext" not in frappe.get_installed_apps():
			self.skipTest("ERPNext is not installed")
		frappe.local.request = None
		lead = frappe.get_doc(
			{"doctype": "Lead", "first_name": "LM Test 3", "email_id": "lm-test-lead3@example.com"}
		).insert()
		self.assertFalse(frappe.db.exists("Marketing Attribution", {"reference_name": lead.name}))

	def test_frappe_crm_lead_form_and_deal(self):
		if "crm" not in frappe.get_installed_apps():
			self.skipTest("Frappe CRM is not installed")
		frappe.get_doc(
			{
				"doctype": "Marketing Lead Form Map",
				"form_id": "lm-form-1",
				"marketing_campaign": self.campaign.name,
			}
		).insert()
		frappe.local.request = None
		lead = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"first_name": "LM Form",
				"email": "lm-form@example.com",
				"facebook_form_id": "lm-form-1",
			}
		).insert()
		self.assertEqual(lead.marketing_campaign, self.campaign.name)
		a = frappe.get_doc(
			"Marketing Attribution", {"reference_doctype": "CRM Lead", "reference_name": lead.name}
		)
		self.assertEqual(a.lead_form, "lm-form-1")
		self.assertEqual(a.last_campaign_link, self.campaign.name)
		frappe.db.set_value("CRM Lead", lead.name, "utm_campaign", "lm-test-expo")
		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"lead": lead.name,
				"email": "lm-form@example.com",
				"first_name": "LM Form",
			}
		)
		deal.insert(ignore_mandatory=True)
		self.assertEqual(deal.marketing_campaign, self.campaign.name)
		self.assertEqual(deal.utm_campaign, "lm-test-expo")
