# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Install and migrate: the Marketing User role, the default channels, and custom fields on the apps that are installed.

ERPNext, Frappe CRM and japan_workplace are optional: their custom fields are created only when the app is present,
including when it is installed after this app (after_app_install).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CHANNELS = [
	# name, type, online, utm_source, utm_medium
	("Meta", "Social", 1, "meta", "paid_social"),
	("Google", "Search", 1, "google", "cpc"),
	("ChatGPT", "Conversational AI", 1, "chatgpt", "paid_ai"),
	("LINE Yahoo", "Display", 1, "lineyahoo", "display"),
	("Microsoft", "Search", 1, "microsoft", "cpc"),
	("TikTok", "Social", 1, "tiktok", "paid_social"),
	("X", "Social", 1, "x", "paid_social"),
	("LinkedIn", "Social", 1, "linkedin", "paid_social"),
	("Exhibition", "Offline", 0, "exhibition", "offline"),
	("Other Offline", "Offline", 0, "offline", "offline"),
]

UTM_FIELDS = [
	{"fieldname": "utm_source", "fieldtype": "Link", "label": "UTM Source", "options": "UTM Source"},
	{"fieldname": "utm_medium", "fieldtype": "Link", "label": "UTM Medium", "options": "UTM Medium"},
	{"fieldname": "utm_campaign", "fieldtype": "Link", "label": "UTM Campaign", "options": "UTM Campaign"},
]


def custom_fields():
	apps = frappe.get_installed_apps()
	fields = {}
	if "erpnext" in apps:
		fields["Marketing Campaign"] = [
			{
				"fieldname": "company",
				"fieldtype": "Link",
				"label": "Company",
				"options": "Company",
				"insert_after": "campaign_owner",
			},
			{
				"fieldname": "cost_center",
				"fieldtype": "Link",
				"label": "Cost Center",
				"options": "Cost Center",
				"insert_after": "currency",
			},
			{
				"fieldname": "project",
				"fieldtype": "Link",
				"label": "Project",
				"options": "Project",
				"insert_after": "cost_center",
			},
		]
		fields["Marketing Ad Account"] = [
			{
				"fieldname": "company",
				"fieldtype": "Link",
				"label": "Company",
				"options": "Company",
				"insert_after": "external_id",
			},
			{
				"fieldname": "supplier",
				"fieldtype": "Link",
				"label": "Supplier",
				"options": "Supplier",
				"insert_after": "agency",
				"description": "The agency or channel that invoices the ad spend",
			},
		]
		fields["Purchase Invoice Item"] = [
			{
				"fieldname": "marketing_campaign",
				"fieldtype": "Link",
				"label": "Marketing Campaign",
				"options": "Marketing Campaign",
				"insert_after": "project",
			},
			{
				"fieldname": "marketing_channel",
				"fieldtype": "Link",
				"label": "Marketing Channel",
				"options": "Marketing Channel",
				"insert_after": "marketing_campaign",
			},
		]
	if "crm" in apps:
		for dt, after in (("CRM Lead", "source"), ("CRM Deal", "source")):
			rows, prev = [], after
			for f in [
				*UTM_FIELDS,
				{
					"fieldname": "marketing_campaign",
					"fieldtype": "Link",
					"label": "Marketing Campaign",
					"options": "Marketing Campaign",
					"read_only": 1,
				},
			]:
				rows.append({**f, "insert_after": prev})
				prev = f["fieldname"]
			fields[dt] = rows
	if "japan_workplace" in apps:
		fields["Marketing Settings"] = [
			{
				"fieldname": "ringi_type",
				"fieldtype": "Link",
				"label": "Ringi Type",
				"options": "Ringi Type",
				"insert_after": "require_ringi",
				"depends_on": "require_ringi",
			}
		]
	return fields


def make_role():
	if not frappe.db.exists("Role", "Marketing User"):
		frappe.get_doc({"doctype": "Role", "role_name": "Marketing User", "desk_access": 1}).insert(
			ignore_permissions=True
		)
	if not frappe.db.exists(
		"Role", "Marketing Manager"
	):  # Frappe ships it; created here only if it is missing
		frappe.get_doc({"doctype": "Role", "role_name": "Marketing Manager", "desk_access": 1}).insert(
			ignore_permissions=True
		)


def make_channels():
	for name, ctype, online, source, medium in CHANNELS:
		for dt, value in (("UTM Source", source), ("UTM Medium", medium)):
			if not frappe.db.exists(dt, value):
				doc = frappe.new_doc(dt)
				doc.name = value
				doc.slug = value
				doc.insert(ignore_permissions=True)
		if not frappe.db.exists("Marketing Channel", name):
			frappe.get_doc(
				{
					"doctype": "Marketing Channel",
					"channel_name": name,
					"channel_type": ctype,
					"is_online": online,
					"utm_source": source,
					"utm_medium": medium,
				}
			).insert(ignore_permissions=True)


def after_install():
	after_migrate()


def after_migrate():
	make_role()
	make_channels()
	create_custom_fields(custom_fields(), ignore_validate=True, update=True)
	from frappe.utils.install import create_desktop_icons_for_app

	create_desktop_icons_for_app()


def after_app_install(app_name):
	if app_name in ("erpnext", "crm", "japan_workplace"):
		create_custom_fields(custom_fields(), ignore_validate=True, update=True)
