# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Ad cost reported by the channels against purchase invoices (ERPNext), by month, campaign and channel.

Purchase invoice items carry the campaign and channel (custom fields of this app). A difference shows invoices that
are missing, late, or tagged to another campaign.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from lifegence_marketing import reports as r

GROUP = ("month", "campaign", "channel")


def execute(filters=None):
	f = frappe._dict(filters or {})
	cols = [
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "campaign",
			"label": _("Marketing Campaign"),
			"fieldtype": "Link",
			"options": "Marketing Campaign",
			"width": 180,
		},
		{
			"fieldname": "channel",
			"label": _("Channel"),
			"fieldtype": "Link",
			"options": "Marketing Channel",
			"width": 120,
		},
		{
			"fieldname": "media_cost",
			"label": _("Cost Reported by the Channel"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{"fieldname": "invoiced", "label": _("Invoiced"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "difference", "label": _("Difference"), "fieldtype": "Currency", "width": 130},
	]
	if not r.installed("erpnext"):
		return cols, [], _("This report needs ERPNext (purchase invoices).")
	cost = r.cost(f.from_date, f.to_date, GROUP, f.campaign, f.channel)
	invoiced = defaultdict(float)
	pii = frappe.qb.DocType("Purchase Invoice Item")
	pi = frappe.qb.DocType("Purchase Invoice")
	q = (
		frappe.qb.from_(pii)
		.join(pi)
		.on(pii.parent == pi.name)
		.select(pi.posting_date, pii.marketing_campaign, pii.marketing_channel, pii.base_net_amount)
		.where(
			(pi.docstatus == 1)
			& (pi.posting_date[f.from_date : f.to_date])
			& pii.marketing_campaign.isnotnull()
		)
	)
	if f.campaign:
		q = q.where(pii.marketing_campaign == f.campaign)
	if f.channel:
		q = q.where(pii.marketing_channel == f.channel)
	for row in q.run(as_dict=True):
		invoiced[(r.month_of(row.posting_date), row.marketing_campaign, row.marketing_channel)] += flt(
			row.base_net_amount
		)
	data = []
	for k in sorted(set(cost) | set(invoiced), key=lambda k: tuple(str(x or "") for x in k)):
		c = cost.get(k, {}).get("cost", 0)
		data.append(
			{
				"month": k[0],
				"campaign": k[1],
				"channel": k[2],
				"media_cost": c,
				"invoiced": invoiced.get(k, 0),
				"difference": flt(c) - flt(invoiced.get(k, 0)),
			}
		)
	return cols, data
