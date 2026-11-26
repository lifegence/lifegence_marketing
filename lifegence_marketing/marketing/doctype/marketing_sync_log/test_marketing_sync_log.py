# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""The connector framework with a fake connector (no network)."""

from typing import ClassVar
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from lifegence_marketing.connectors import get_connector
from lifegence_marketing.connectors.base import AuthError, MarketingConnector
from lifegence_marketing.connectors.sync import retry_failed, sync_account, window
from lifegence_marketing.marketing.doctype.marketing_campaign.test_marketing_campaign import make_campaign

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Marketing Ad Account",
	"Marketing Channel",
	"Marketing Campaign",
	"UTM Campaign",
	"UTM Source",
	"UTM Medium",
	"Currency",
	"User",
	"Company",
	"Supplier",
	"Connected App",
]

CHANNEL = "LM Test Channel"
MANAGER = "lm-test-manager@example.com"
PATH = "lifegence_marketing.marketing.doctype.marketing_sync_log.test_marketing_sync_log.FakeConnector"


class FakeConnector(MarketingConnector):
	key = "fake"
	label = "Fake"
	channel = CHANNEL
	auth_type = "api_key"
	supports_leads = True
	mode = "ok"  # ok / auth / boom
	calls: ClassVar[list] = []

	def test_connection(self, account):
		return "ok " + self.access_token(account)

	def fetch_performance(self, account, date_from, date_to):
		FakeConnector.calls.append((str(date_from), str(date_to)))
		if FakeConnector.mode == "auth":
			raise AuthError("token revoked")
		if FakeConnector.mode == "boom":
			raise RuntimeError("API changed")
		return [
			{
				"date": date_to,
				"campaign_id": "c1",
				"campaign_name": "lm-test-expo_api",
				"ad_id": "a1",
				"ad_name": "Ad 1",
				"placement": "instagram",
				"impressions": 100,
				"clicks": 5,
				"cost": 1200,
				"conversions": 1,
			},
			{
				"date": date_to,
				"campaign_id": "c1",
				"campaign_name": "lm-test-expo_api",
				"ad_id": "a2",
				"ad_name": "Ad 2",
				"impressions": 50,
				"clicks": 1,
				"cost": 300,
			},
		]

	def fetch_leads(self, account, since):
		return [
			{
				"external_id": "lead-1",
				"form_id": "lm-sync-form",
				"first_name": "Taro",
				"email": "lm-sync-taro@example.com",
				"created": "2026-11-20 10:00:00",
			},
			{
				"external_id": "lead-2",
				"campaign_id": "c1",
				"first_name": "Hanako",
				"email": "lm-sync-hanako@example.com",
			},
		]


def cleanup():
	accounts = frappe.get_all("Marketing Ad Account", filters={"channel": CHANNEL}, pluck="name")
	if accounts:
		for dt in ("Marketing Sync Log", "Marketing Performance", "Marketing Ad Object"):
			frappe.db.delete(dt, {"ad_account": ("in", accounts)})
		frappe.db.delete("Notification Log", {"document_name": ("in", accounts)})
	for a in frappe.get_all(
		"Marketing Attribution",
		filters={"external_lead_id": ("in", ["lead-1", "lead-2"])},
		fields=["name", "reference_doctype", "reference_name"],
	):
		if frappe.db.exists(a.reference_doctype, a.reference_name):
			frappe.delete_doc(a.reference_doctype, a.reference_name, force=True, ignore_permissions=True)
		frappe.db.delete("Marketing Attribution", a.name)
	frappe.db.delete("Marketing Lead Form Map", {"form_id": "lm-sync-form"})
	frappe.db.commit()


class TestConnectorFramework(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cleanup()
		if not frappe.db.exists("Marketing Channel", CHANNEL):
			frappe.get_doc(
				{"doctype": "Marketing Channel", "channel_name": CHANNEL, "channel_type": "Social"}
			).insert()
		frappe.db.set_value("Marketing Channel", CHANNEL, "connector", "fake")
		if not frappe.db.exists("User", MANAGER):
			frappe.get_doc(
				{"doctype": "User", "email": MANAGER, "first_name": "LM Manager", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", MANAGER).add_roles("Marketing Manager")
		cls.campaign = make_campaign()
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		cleanup()
		super().tearDownClass()

	def setUp(self):
		FakeConnector.mode = "ok"
		FakeConnector.calls = []
		name = frappe.db.get_value("Marketing Ad Account", {"channel": CHANNEL, "external_id": "lm-fake-1"})
		if name:
			frappe.delete_doc("Marketing Ad Account", name, force=True)
		self.account = frappe.get_doc(
			{
				"doctype": "Marketing Ad Account",
				"account_name": "LM Fake",
				"channel": CHANNEL,
				"external_id": "lm-fake-1",
				"currency": "JPY",
				"sync_enabled": 1,
				"api_key": "secret-key",
			}
		).insert()
		frappe.db.commit()
		self.patcher = patch("lifegence_marketing.connectors.registry", return_value={"fake": PATH})
		self.patcher.start()

	def tearDown(self):
		self.patcher.stop()
		cleanup()

	def test_registry_and_api_key(self):
		self.assertIsInstance(get_connector("fake"), FakeConnector)
		with self.assertRaises(frappe.ValidationError):
			get_connector("nothing")
		self.assertEqual(get_connector("fake").test_connection(self.account), "ok secret-key")

	def test_import_writes_figures_and_log(self):
		log = frappe.get_doc("Marketing Sync Log", sync_account(self.account.name))
		self.assertEqual((log.status, log.rows, log.connector), ("Done", 2, "fake"))
		rows = frappe.get_all(
			"Marketing Performance",
			filters={"ad_account": self.account.name},
			fields=["source", "cost", "placement", "marketing_campaign"],
			order_by="cost desc",
		)
		self.assertEqual(
			[(r.source, r.cost, r.placement, r.marketing_campaign) for r in rows],
			[("API", 1200, "instagram", "lm-test-expo"), ("API", 300, None, "lm-test-expo")],
		)
		acc = frappe.get_doc("Marketing Ad Account", self.account.name)
		self.assertEqual(acc.sync_status, "OK")
		self.assertTrue(acc.last_synced_on)
		sync_account(self.account.name)  # again: replaced, not added
		self.assertEqual(frappe.db.count("Marketing Performance", {"ad_account": self.account.name}), 2)

	def test_window(self):
		start, end = window(self.account)
		self.assertEqual(end, getdate(nowdate()))
		self.assertEqual(start, getdate(add_days(nowdate(), -89)))  # first import: 90 days
		self.account.last_synced_on = frappe.utils.now_datetime()
		start, _end = window(self.account)
		self.assertEqual(start, getdate(add_days(nowdate(), -6)))  # then the last 7 days
		self.assertEqual(
			window(self.account, "2026-04-01", "2026-04-30"), (getdate("2026-04-01"), getdate("2026-04-30"))
		)

	def test_expired_connection(self):
		FakeConnector.mode = "auth"
		log = frappe.get_doc("Marketing Sync Log", sync_account(self.account.name))
		self.assertEqual(log.status, "Failed")
		self.assertIn("token revoked", log.error)
		self.assertEqual(
			frappe.db.get_value("Marketing Ad Account", self.account.name, "sync_status"), "Auth Expired"
		)
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": MANAGER, "document_name": self.account.name})
		)
		self.assertIsNone(frappe.db.get_value("Marketing Ad Account", self.account.name, "last_synced_on"))

	def test_failure_is_retried_up_to_three_times_a_day(self):
		FakeConnector.mode = "boom"
		sync_account(self.account.name)
		self.assertEqual(
			frappe.db.get_value("Marketing Ad Account", self.account.name, "sync_status"), "Error"
		)
		with patch("lifegence_marketing.connectors.sync.frappe.enqueue") as enqueue:
			retry_failed()
			self.assertEqual(
				[
					c.kwargs["name"]
					for c in enqueue.call_args_list
					if c.kwargs.get("name") == self.account.name
				],
				[self.account.name],
			)
		sync_account(self.account.name)
		sync_account(self.account.name)
		with patch("lifegence_marketing.connectors.sync.frappe.enqueue") as enqueue:
			retry_failed()
			self.assertFalse([c for c in enqueue.call_args_list if c.kwargs.get("name") == self.account.name])

	def test_leads(self):
		apps = frappe.get_installed_apps()
		if "crm" not in apps and "erpnext" not in apps:
			self.skipTest("Neither Frappe CRM nor ERPNext is installed")
		frappe.get_doc(
			{
				"doctype": "Marketing Lead Form Map",
				"channel": CHANNEL,
				"form_id": "lm-sync-form",
				"marketing_campaign": self.campaign.name,
			}
		).insert()
		frappe.db.commit()
		log = frappe.get_doc("Marketing Sync Log", sync_account(self.account.name))
		self.assertEqual(log.leads, 2)
		a1 = frappe.get_doc("Marketing Attribution", {"external_lead_id": "lead-1"})
		self.assertEqual(a1.reference_doctype, "CRM Lead" if "crm" in apps else "Lead")
		self.assertEqual(a1.last_campaign_link, self.campaign.name)  # from the form map
		self.assertEqual(str(a1.recorded_on), "2026-11-20 10:00:00")
		a2 = frappe.get_doc("Marketing Attribution", {"external_lead_id": "lead-2"})
		self.assertEqual(a2.last_campaign_link, self.campaign.name)  # from the channel's campaign c1
		log = frappe.get_doc("Marketing Sync Log", sync_account(self.account.name))
		self.assertEqual(log.leads, 0)  # known leads are skipped
