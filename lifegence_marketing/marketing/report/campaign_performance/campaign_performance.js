// Copyright (c) 2026, Lifegence Corporation
// License: Apache-2.0. See license.txt

frappe.query_reports["Campaign Performance"] = {
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
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Campaign", "Channel", "Campaign and Channel"],
			default: "Campaign",
		},
		{
			fieldname: "attribution",
			label: __("Attribution"),
			fieldtype: "Select",
			options: ["", "Last Touch", "First Touch"],
		},
	],
};
