// Copyright (c) 2026, Lifegence Corporation
// License: Apache-2.0. See license.txt

frappe.query_reports["Ad Spend Reconciliation"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "campaign",
			label: __("Marketing Campaign"),
			fieldtype: "Link",
			options: "Marketing Campaign",
		},
		{
			fieldname: "channel",
			label: __("Channel"),
			fieldtype: "Link",
			options: "Marketing Channel",
		},
	],
};
