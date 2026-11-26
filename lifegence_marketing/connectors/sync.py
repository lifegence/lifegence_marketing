# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Running connectors: the daily import, the hourly retry, the log and the notices."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime, nowdate

from lifegence_marketing.connectors import get_connector
from lifegence_marketing.connectors.base import AuthError, ConnectorError
from lifegence_marketing.performance import Saver

MAX_RETRIES = 3


def accounts_to_sync():
	return frappe.get_all(
		"Marketing Ad Account",
		filters={"sync_enabled": 1, "disabled": 0},
		fields=["name", "channel"],
	)


def window(account, date_from=None, date_to=None):
	"""The period to fetch: the last refresh_days (figures are revised late), or backfill_days on the first import."""
	if date_from and date_to:
		return getdate(date_from), getdate(date_to)
	s = frappe.get_cached_doc("Marketing Settings")
	if account.last_synced_on:
		days = cint(s.refresh_days) or 7
	else:
		days = cint(s.backfill_days) or 90
	end = getdate(nowdate())
	return getdate(add_days(end, -(days - 1))), end


def connector_for(account):
	key = frappe.db.get_value("Marketing Channel", account.channel, "connector")
	if not key:
		raise ConnectorError(_("Channel {0} has no connector").format(account.channel))
	return get_connector(key)


def sync_account(name, date_from=None, date_to=None):
	"""Import one ad account. Returns the Marketing Sync Log name."""
	account = frappe.get_doc("Marketing Ad Account", name)
	start, end = window(account, date_from, date_to)
	log = frappe.get_doc(
		{
			"doctype": "Marketing Sync Log",
			"ad_account": name,
			"date_from": start,
			"date_to": end,
			"status": "Running",
			"started_on": now_datetime(),
		}
	).insert(ignore_permissions=True)
	# The "Running" log must survive the rollback below when the import fails
	frappe.db.commit()  # nosemgrep
	status, rows, leads, error = "OK", 0, 0, None
	try:
		connector = connector_for(account)
		log.db_set("connector", connector.key)
		saver = Saver(name, "API")
		for row in connector.fetch_performance(account, start, end):
			saver.save(row)
			rows += 1
		if connector.supports_leads:
			leads = save_leads(account, connector.fetch_leads(account, account.last_synced_on))
	except AuthError as e:
		frappe.db.rollback()
		status, error = "Auth Expired", str(e)
	except ConnectorError as e:
		frappe.db.rollback()
		status, error = "Error", str(e)
	except Exception:
		frappe.db.rollback()
		status, error = "Error", frappe.get_traceback()
	log.db_set(
		{
			"status": "Done" if status == "OK" else "Failed",
			"rows": rows,
			"leads": leads,
			"error": error,
			"finished_on": now_datetime(),
		}
	)
	values = {"sync_status": status}
	if status == "OK":
		values["last_synced_on"] = now_datetime()
	frappe.db.set_value("Marketing Ad Account", name, values, update_modified=False)
	if status != "OK":
		notify_failure(account, status, error)
	return log.name


def notify_failure(account, status, error):
	subject = (
		_("Ad account {0}: the connection has expired. Connect it again.").format(account.account_name)
		if status == "Auth Expired"
		else _("Ad account {0}: the import failed.").format(account.account_name)
	)
	users = set(
		frappe.get_all(
			"Has Role", filters={"role": "Marketing Manager", "parenttype": "User"}, pluck="parent"
		)
	)
	users = {
		u for u in users if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
	}
	for user in users:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Marketing Ad Account",
				"document_name": account.name,
				"subject": subject,
				"email_content": (error or "")[:1000],
			}
		).insert(ignore_permissions=True)


def save_leads(account, leads):
	"""Leads from a channel's lead form: a Frappe CRM lead if Frappe CRM is installed, else an ERPNext lead.

	Leads already known (by their external ID) are skipped. Each gets a Marketing Attribution with the form and the
	campaign matched through Marketing Lead Form Map or the channel's campaign.
	"""
	apps = frappe.get_installed_apps()
	doctype = "CRM Lead" if "crm" in apps else "Lead" if "erpnext" in apps else None
	if not doctype:
		return 0
	count = 0
	for lead in leads or []:
		ext = str(lead.get("external_id") or "")
		if not ext or frappe.db.exists("Marketing Attribution", {"external_lead_id": ext}):
			continue
		campaign = (
			lead.get("form_id")
			and frappe.db.get_value(
				"Marketing Lead Form Map", {"form_id": lead["form_id"]}, "marketing_campaign"
			)
		) or campaign_of_object(account, lead.get("campaign_id"))
		values = {
			"first_name": lead.get("first_name") or lead.get("email") or ext,
			"last_name": lead.get("last_name"),
		}
		if doctype == "CRM Lead":
			values.update(
				email=lead.get("email"),
				mobile_no=lead.get("phone"),
				organization=lead.get("company"),
				source=None,
			)
			if frappe.get_meta("CRM Lead").has_field("marketing_campaign"):
				values["marketing_campaign"] = campaign
		else:
			values.update(
				email_id=lead.get("email"), mobile_no=lead.get("phone"), company_name=lead.get("company")
			)
			if campaign:
				values["utm_campaign"] = frappe.db.get_value("Marketing Campaign", campaign, "utm_campaign")
		doc = frappe.get_doc({"doctype": doctype, **{k: v for k, v in values.items() if v is not None}})
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Marketing Attribution",
				"reference_doctype": doctype,
				"reference_name": doc.name,
				"external_lead_id": ext,
				"lead_form": lead.get("form_id"),
				"first_source": account.channel.lower(),
				"last_source": account.channel.lower(),
				"first_campaign_link": campaign,
				"last_campaign_link": campaign,
				"recorded_on": get_datetime(lead.get("created")) if lead.get("created") else now_datetime(),
			}
		).insert(ignore_permissions=True)
		count += 1
	return count


def campaign_of_object(account, external_id):
	if not external_id:
		return None
	return frappe.db.get_value(
		"Marketing Ad Object",
		{"ad_account": account.name, "object_type": "Campaign", "external_id": str(external_id)},
		"marketing_campaign",
	)


def daily():
	for a in accounts_to_sync():
		frappe.enqueue(sync_account, queue="long", name=a.name, job_id=f"lm-sync-{a.name}", deduplicate=True)


def retry_failed():
	"""Hourly: accounts whose last import failed (not for expired connections), up to MAX_RETRIES a day."""
	for a in frappe.get_all(
		"Marketing Ad Account",
		filters={"sync_enabled": 1, "disabled": 0, "sync_status": "Error"},
		pluck="name",
	):
		failed_today = frappe.db.count(
			"Marketing Sync Log", {"ad_account": a, "status": "Failed", "creation": (">=", nowdate())}
		)
		if failed_today < MAX_RETRIES:
			frappe.enqueue(sync_account, queue="long", name=a, job_id=f"lm-sync-{a}", deduplicate=True)


@frappe.whitelist(methods=["POST"])
def sync_now(name: str, date_from: str | None = None, date_to: str | None = None):
	frappe.get_doc("Marketing Ad Account", name).check_permission("write")
	frappe.enqueue(
		sync_account,
		queue="long",
		name=name,
		date_from=date_from,
		date_to=date_to,
		job_id=f"lm-sync-{name}",
		deduplicate=True,
	)


@frappe.whitelist(methods=["POST"])
def test_connection(name: str):
	account = frappe.get_doc("Marketing Ad Account", name)
	account.check_permission("write")
	try:
		return {"ok": True, "message": connector_for(account).test_connection(account)}
	except ConnectorError as e:
		return {"ok": False, "message": str(e)}
