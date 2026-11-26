# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Budget and ad cost by campaign, channel and month, with the forecast for the current month (cost so far, per day)."""

import calendar

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from lifegence_marketing import reports as r

GROUP = ("campaign", "channel", "month")


def forecast(month, spent, today=None):
	"""The current month is extrapolated from the cost so far (per day); other months are what was spent."""
	today = getdate(today or nowdate())
	m = getdate(month)
	if (m.year, m.month) != (today.year, today.month):
		return flt(spent)
	return flt(spent) / today.day * calendar.monthrange(m.year, m.month)[1]


def execute(filters=None):
	f = frappe._dict(filters or {})
	budget = r.budget(f.from_date, f.to_date, GROUP, f.campaign, f.channel)
	cost = r.cost(f.from_date, f.to_date, GROUP, f.campaign, f.channel)
	data = []
	for k in sorted(set(budget) | set(cost), key=lambda k: tuple(str(x or "") for x in k)):
		b, c = budget.get(k, 0), cost.get(k, {}).get("cost", 0)
		fc = forecast(k[2], c) if k[2] else c
		data.append(
			{
				"campaign": k[0],
				"channel": k[1],
				"month": k[2],
				"budget": b,
				"cost": c,
				"used": r.ratio(c, b, 100),
				"forecast": fc,
				"forecast_vs_budget": r.ratio(fc, b, 100),
				"remaining": flt(b) - flt(c),
			}
		)
	cur = {"fieldtype": "Currency", "width": 120}
	cols = [
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
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Date", "width": 100},
		{"fieldname": "budget", "label": _("Budget"), **cur},
		{"fieldname": "cost", "label": _("Cost"), **cur},
		{"fieldname": "used", "label": _("Used %"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "forecast", "label": _("Forecast for the Month"), **cur},
		{
			"fieldname": "forecast_vs_budget",
			"label": _("Forecast vs Budget %"),
			"fieldtype": "Percent",
			"width": 110,
		},
		{"fieldname": "remaining", "label": _("Remaining"), **cur},
	]
	return cols, data
