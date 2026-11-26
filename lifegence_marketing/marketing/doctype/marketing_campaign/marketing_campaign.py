# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""A marketing campaign: objective, period, budget by channel and month, and targets.

The campaign code is the key that ties everything together: it is the name of the campaign, the name and slug of
Frappe's UTM Campaign (which ERPNext and Frappe CRM documents link to as utm_campaign) and the utm_campaign value of
tracking links.
"""

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, getdate

CODE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
OPEN_STATES = ("Planned", "Pending Approval")


def normalize_code(value):
	return re.sub(r"-+", "-", re.sub(r"[\s_]+", "-", (value or "").strip().lower()))


class MarketingCampaign(Document):
	def onload(self):
		if ringi_required():
			self.set_onload(
				"ringi", {"required": 1, "decided": decided_ringi(self.name), "type": ringi_type()}
			)

	def before_insert(self):
		self.campaign_code = normalize_code(self.campaign_code)
		if not CODE.match(self.campaign_code or ""):
			frappe.throw(
				_(
					"The campaign code may contain only lowercase letters, digits and hyphens (2 to 63 characters)"
				)
			)
		self.utm_campaign = ensure_utm_campaign(self.campaign_code, self.campaign_name)

	def validate(self):
		if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must not be before From Date"))
		seen = set()
		for row in self.budgets:
			row.month = get_first_day(row.month)
			key = (row.channel, str(row.month))
			if key in seen:
				frappe.throw(
					_("Row {0}: {1} in {2} is listed more than once").format(row.idx, row.channel, row.month)
				)
			seen.add(key)
			if flt(row.amount) < 0:
				frappe.throw(_("Row {0}: the budget cannot be negative").format(row.idx))
		self.total_budget = sum(flt(r.amount) for r in self.budgets)
		self.check_activation()

	def check_activation(self):
		before = self.get_doc_before_save()
		if self.status != "Active" or (before and before.status == "Active"):
			return
		if ringi_required() and not decided_ringi(self.name):
			frappe.throw(
				_("A decided ringi that references this campaign is needed to make it Active"),
				title=_("Approval needed"),
			)


def ensure_utm_campaign(code, description=None):
	if not frappe.db.exists("UTM Campaign", code):
		doc = frappe.new_doc("UTM Campaign")
		doc.name = code
		doc.slug = code
		doc.campaign_description = description
		doc.insert(ignore_permissions=True)
	return code


def ringi_required():
	if not frappe.db.get_single_value("Marketing Settings", "require_ringi"):
		return False
	# japan_workplace may be listed on a site that has not been migrated since it gained the ringi
	return "japan_workplace" in frappe.get_installed_apps() and frappe.db.table_exists("Ringi")


def ringi_type():
	meta = frappe.get_meta("Marketing Settings")
	return (
		frappe.db.get_single_value("Marketing Settings", "ringi_type")
		if meta.has_field("ringi_type")
		else None
	)


def decided_ringi(campaign):
	filters = {"reference_doctype": "Marketing Campaign", "reference_name": campaign, "status": "Decided"}
	rtype = ringi_type()
	if rtype:
		filters["ringi_type"] = rtype
	return frappe.db.get_value("Ringi", filters, "name")


def on_ringi_update(doc, method=None):
	"""A decided ringi for a campaign waiting for approval: tell the campaign owner it can be made Active."""
	if doc.get("reference_doctype") != "Marketing Campaign" or doc.get("status") != "Decided":
		return
	before = doc.get_doc_before_save()
	if before and before.status == "Decided":
		return
	campaign = frappe.db.get_value(
		"Marketing Campaign",
		doc.reference_name,
		["name", "campaign_name", "campaign_owner", "status"],
		as_dict=True,
	)
	if not campaign or not campaign.campaign_owner or campaign.status not in OPEN_STATES:
		return
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": campaign.campaign_owner,
			"type": "Alert",
			"document_type": "Marketing Campaign",
			"document_name": campaign.name,
			"subject": _("The ringi for {0} was decided. The campaign can be made Active.").format(
				campaign.campaign_name
			),
		}
	).insert(ignore_permissions=True)
