# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Cost, leads, cost per lead, revenue and ROAS by channel and month."""

from collections import defaultdict

import frappe
from frappe import _

from lifegence_marketing import reports as r

GROUP = ("channel", "month")


def execute(filters=None):
	f = frappe._dict(filters or {})
	model = f.attribution or frappe.db.get_single_value("Marketing Settings", "default_model") or "Last Touch"
	cost = r.cost(f.from_date, f.to_date, GROUP)
	leads = defaultdict(int)
	lead_rows = r.leads(f.from_date, f.to_date, model)
	deals = r.deals(lead_rows)
	won_amount = defaultdict(float)
	for x in lead_rows:
		k = (x.channel, x.month)
		leads[k] += 1
		won_amount[k] += sum(d.amount for d in deals.get((x.doctype, x.name), []) if d.won)
	revenue = won_amount if not r.installed("erpnext") else r.revenue(f.from_date, f.to_date, GROUP)
	data = []
	for k in sorted(set(cost) | set(leads) | set(revenue), key=lambda k: tuple(str(x or "") for x in k)):
		c = cost.get(k, {}).get("cost", 0)
		data.append(
			{
				"channel": k[0],
				"month": k[1],
				"cost": c,
				"clicks": cost.get(k, {}).get("clicks", 0),
				"leads": leads.get(k, 0),
				"cpa": r.ratio(c, leads.get(k)),
				"revenue": revenue.get(k, 0),
				"roas": r.ratio(revenue.get(k), c),
			}
		)
	cur = {"fieldtype": "Currency", "width": 120}
	cols = [
		{
			"fieldname": "channel",
			"label": _("Channel"),
			"fieldtype": "Link",
			"options": "Marketing Channel",
			"width": 130,
		},
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Date", "width": 100},
		{"fieldname": "cost", "label": _("Cost"), **cur},
		{"fieldname": "clicks", "label": _("Clicks"), "fieldtype": "Int", "width": 90},
		{"fieldname": "leads", "label": _("Leads"), "fieldtype": "Int", "width": 80},
		{"fieldname": "cpa", "label": _("Cost per Lead"), **cur},
		{"fieldname": "revenue", "label": _("Revenue"), **cur},
		{"fieldname": "roas", "label": _("ROAS"), "fieldtype": "Float", "precision": 2, "width": 80},
	]
	chart = {
		"data": {
			"labels": sorted({d["month"] for d in data if d["month"]}),
			"datasets": [
				{
					"name": ch or _("Not Set"),
					"values": [
						sum(d["cost"] for d in data if d["channel"] == ch and d["month"] == m)
						for m in sorted({d["month"] for d in data if d["month"]})
					],
				}
				for ch in sorted({d["channel"] for d in data}, key=lambda x: x or "")
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}
	return cols, data, None, chart
