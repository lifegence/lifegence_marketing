# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Data for the reports: ad cost, leads, deals and revenue by campaign, channel and month.

- Cost, impressions, clicks: Marketing Performance.
- Leads: Marketing Attribution (first or last touch), by the date it was recorded.
- Deals: Frappe CRM deals of those leads (won = a status of type Won), or ERPNext opportunities from those leads
  (won = Converted).
- Revenue: submitted ERPNext sales invoices by their utm_campaign and utm_source (carried from the lead through
  opportunity, quotation and order). Without ERPNext, the value of won Frappe CRM deals.
Apps that are not installed simply contribute nothing.
"""

from collections import defaultdict

import frappe
from frappe.utils import flt, get_first_day, getdate


def installed(app):
	return app in frappe.get_installed_apps()


def channel_by_source():
	return {
		r.utm_source: r.name
		for r in frappe.get_all("Marketing Channel", fields=["name", "utm_source"])
		if r.utm_source
	}


def key_of(group, campaign, channel, month=None):
	parts = {"campaign": campaign, "channel": channel, "month": month}
	return tuple(parts[g] for g in group)


def month_of(d):
	return str(get_first_day(d)) if d else None


def cost(from_date, to_date, group, campaign=None, channel=None):
	filters = {"date": ("between", [from_date, to_date])}
	if campaign:
		filters["marketing_campaign"] = campaign
	if channel:
		filters["channel"] = channel
	out = defaultdict(lambda: defaultdict(float))
	for r in frappe.get_all(
		"Marketing Performance",
		filters=filters,
		fields=["marketing_campaign", "channel", "date", "cost", "impressions", "clicks", "conversions"],
	):
		k = key_of(group, r.marketing_campaign, r.channel, month_of(r.date))
		for f in ("cost", "impressions", "clicks", "conversions"):
			out[k][f] += flt(r[f])
	return out


def leads(from_date, to_date, model="Last Touch", campaign=None):
	"""Attributed leads: [{doctype, name, campaign, channel, month}]."""
	prefix = "first" if model == "First Touch" else "last"
	sources = channel_by_source()
	filters = {"recorded_on": ("between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"])}
	if campaign:
		filters[f"{prefix}_campaign_link"] = campaign
	rows = frappe.get_all(
		"Marketing Attribution",
		filters=filters,
		fields=[
			"reference_doctype",
			"reference_name",
			f"{prefix}_campaign_link as campaign",
			f"{prefix}_source as source",
			"recorded_on",
			"lead_form",
		],
	)
	meta = frappe.db.get_value("Marketing Channel", "Meta", "name")
	return [
		frappe._dict(
			doctype=r.reference_doctype,
			name=r.reference_name,
			campaign=r.campaign,
			channel=sources.get(r.source) or (meta if r.lead_form else None),
			month=month_of(r.recorded_on),
		)
		for r in rows
	]


def deals(lead_rows):
	"""{(lead doctype, lead name): [{won, amount}]} for Frappe CRM deals and ERPNext opportunities."""
	out = defaultdict(list)
	crm = [r.name for r in lead_rows if r.doctype == "CRM Lead"]
	if crm and installed("crm"):
		won_states = set(frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name"))
		for d in frappe.get_all(
			"CRM Deal", filters={"lead": ("in", crm)}, fields=["lead", "status", "deal_value"]
		):
			out[("CRM Lead", d.lead)].append(
				frappe._dict(won=d.status in won_states, amount=flt(d.deal_value))
			)
	erp = [r.name for r in lead_rows if r.doctype == "Lead"]
	if erp and installed("erpnext"):
		for o in frappe.get_all(
			"Opportunity",
			filters={"opportunity_from": "Lead", "party_name": ("in", erp), "docstatus": ("<", 2)},
			fields=["party_name", "status", "base_opportunity_amount"],
		):
			out[("Lead", o.party_name)].append(
				frappe._dict(won=o.status == "Converted", amount=flt(o.base_opportunity_amount))
			)
	return out


def revenue(from_date, to_date, group, campaign=None):
	"""Submitted sales invoices by utm_campaign (the campaign code) and utm_source."""
	out = defaultdict(float)
	if not installed("erpnext"):
		return out
	sources = channel_by_source()
	codes = set(frappe.get_all("Marketing Campaign", pluck="name"))
	filters = {
		"docstatus": 1,
		"posting_date": ("between", [from_date, to_date]),
		"utm_campaign": ("is", "set"),
	}
	if campaign:
		filters["utm_campaign"] = campaign
	for si in frappe.get_all(
		"Sales Invoice",
		filters=filters,
		fields=["utm_campaign", "utm_source", "base_net_total", "posting_date"],
	):
		if si.utm_campaign not in codes:
			continue
		out[key_of(group, si.utm_campaign, sources.get(si.utm_source), month_of(si.posting_date))] += flt(
			si.base_net_total
		)
	return out


def budget(from_date, to_date, group, campaign=None, channel=None):
	start, end = get_first_day(from_date), getdate(to_date)
	filters = {"parenttype": "Marketing Campaign", "month": ("between", [start, end])}
	if campaign:
		filters["parent"] = campaign
	if channel:
		filters["channel"] = channel
	out = defaultdict(float)
	for b in frappe.get_all(
		"Marketing Campaign Budget", filters=filters, fields=["parent", "channel", "month", "amount"]
	):
		out[key_of(group, b.parent, b.channel, month_of(b.month))] += flt(b.amount)
	return out


def ratio(a, b, scale=1):
	return flt(a) / flt(b) * scale if flt(b) else None
