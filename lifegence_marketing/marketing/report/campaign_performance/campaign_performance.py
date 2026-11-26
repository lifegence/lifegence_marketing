# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Cost, leads, deals and revenue by campaign and channel, with cost per lead (CPA), deal rate and ROAS."""

from collections import defaultdict

import frappe
from frappe import _

from lifegence_marketing import reports as r

GROUPS = {"Campaign": ("campaign",), "Channel": ("channel",), "Campaign and Channel": ("campaign", "channel")}


def execute(filters=None):
	f = frappe._dict(filters or {})
	group = GROUPS.get(f.group_by or "Campaign", ("campaign",))
	model = f.attribution or frappe.db.get_single_value("Marketing Settings", "default_model") or "Last Touch"
	cost = r.cost(f.from_date, f.to_date, group, f.campaign, f.channel)
	budget = r.budget(f.from_date, f.to_date, group, f.campaign, f.channel)
	revenue = r.revenue(f.from_date, f.to_date, group, f.campaign)
	lead_rows = [
		x
		for x in r.leads(f.from_date, f.to_date, model, f.campaign)
		if not f.channel or x.channel == f.channel
	]
	deals = r.deals(lead_rows)
	agg = defaultdict(lambda: defaultdict(float))
	for x in lead_rows:
		k = r.key_of(group, x.campaign, x.channel)
		agg[k]["leads"] += 1
		for d in deals.get((x.doctype, x.name), []):
			agg[k]["deals"] += 1
			if d.won:
				agg[k]["won"] += 1
				agg[k]["won_amount"] += d.amount
	use_deal_value = not r.installed("erpnext")
	keys = set(cost) | set(budget) | set(revenue) | set(agg)
	if f.channel:
		keys = {k for k in keys if "channel" not in group or k[group.index("channel")] == f.channel}
	data = []
	for k in sorted(keys, key=lambda k: tuple(str(x or "") for x in k)):
		c, a = cost.get(k, {}), agg.get(k, {})
		rev = a.get("won_amount", 0) if use_deal_value else revenue.get(k, 0)
		row = dict(zip(group, k, strict=True))
		row.update(
			budget=budget.get(k, 0),
			cost=c.get("cost", 0),
			impressions=c.get("impressions", 0),
			clicks=c.get("clicks", 0),
			ctr=r.ratio(c.get("clicks"), c.get("impressions"), 100),
			leads=a.get("leads", 0),
			cpa=r.ratio(c.get("cost"), a.get("leads")),
			deals=a.get("deals", 0),
			deal_rate=r.ratio(a.get("deals"), a.get("leads"), 100),
			won=a.get("won", 0),
			won_amount=a.get("won_amount", 0),
			revenue=rev,
			roas=r.ratio(rev, c.get("cost")),
		)
		data.append(row)
	return columns(group, use_deal_value), data


def columns(group, use_deal_value):
	cols = []
	if "campaign" in group:
		cols.append(
			{
				"fieldname": "campaign",
				"label": _("Marketing Campaign"),
				"fieldtype": "Link",
				"options": "Marketing Campaign",
				"width": 180,
			}
		)
	if "channel" in group:
		cols.append(
			{
				"fieldname": "channel",
				"label": _("Channel"),
				"fieldtype": "Link",
				"options": "Marketing Channel",
				"width": 120,
			}
		)
	cur = {"fieldtype": "Currency", "width": 120}
	cols += [
		{"fieldname": "budget", "label": _("Budget"), **cur},
		{"fieldname": "cost", "label": _("Cost"), **cur},
		{"fieldname": "impressions", "label": _("Impressions"), "fieldtype": "Int", "width": 110},
		{"fieldname": "clicks", "label": _("Clicks"), "fieldtype": "Int", "width": 90},
		{"fieldname": "ctr", "label": _("CTR %"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "leads", "label": _("Leads"), "fieldtype": "Int", "width": 80},
		{"fieldname": "cpa", "label": _("Cost per Lead"), **cur},
		{"fieldname": "deals", "label": _("Deals"), "fieldtype": "Int", "width": 80},
		{"fieldname": "deal_rate", "label": _("Deal Rate %"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "won", "label": _("Won"), "fieldtype": "Int", "width": 70},
		{"fieldname": "won_amount", "label": _("Won Amount"), **cur},
		{
			"fieldname": "revenue",
			"label": _("Revenue (Won Deals)") if use_deal_value else _("Revenue (Sales Invoices)"),
			**cur,
		},
		{"fieldname": "roas", "label": _("ROAS"), "fieldtype": "Float", "precision": 2, "width": 80},
	]
	return cols
