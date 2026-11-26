# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Saving ad performance: the channel's objects (campaign > ad group > ad) and the daily figures.

Used by the CSV import and by connectors alike. A row is a dict with any of: date, campaign_id, campaign_name,
ad_group_id, ad_group_name, ad_id, ad_name, placement, impressions, reach, clicks, cost, conversions,
conversion_value, currency. Figures are written over (date, ad account, ad, placement, source): importing the same
period again replaces it.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

LEVELS = (("Campaign", "campaign"), ("Ad Group", "ad_group"), ("Ad", "ad"))
FIGURES = ("impressions", "reach", "clicks", "cost", "conversions", "conversion_value")


class Saver:
	def __init__(self, ad_account, source, batch=None):
		self.account = frappe.get_cached_doc("Marketing Ad Account", ad_account)
		self.source = source
		self.batch = batch
		self.objects = {}  # (type, external id) -> (name, marketing campaign)
		self.separator = frappe.db.get_single_value("Marketing Settings", "campaign_prefix_separator") or "_"
		self.codes = set(frappe.get_all("Marketing Campaign", pluck="name"))

	def object(self, object_type, external_id, title, parent):
		key = (object_type, external_id)
		if key in self.objects:
			return self.objects[key]
		row = frappe.db.get_value(
			"Marketing Ad Object",
			{"ad_account": self.account.name, "object_type": object_type, "external_id": external_id},
			["name", "object_name", "parent_object", "marketing_campaign", "mapped_manually"],
			as_dict=True,
		)
		parent_name, parent_campaign = parent or (None, None)
		if row:
			if title and row.object_name != title:
				frappe.db.set_value(
					"Marketing Ad Object", row.name, "object_name", title, update_modified=False
				)
			campaign = row.marketing_campaign
			if not campaign and not row.mapped_manually:
				campaign = self.match(title) or parent_campaign
				if campaign:
					frappe.db.set_value(
						"Marketing Ad Object", row.name, "marketing_campaign", campaign, update_modified=False
					)
			result = (row.name, campaign)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Marketing Ad Object",
					"ad_account": self.account.name,
					"object_type": object_type,
					"external_id": external_id,
					"object_name": title or external_id,
					"parent_object": parent_name,
					"marketing_campaign": self.match(title) or parent_campaign,
				}
			)
			doc.flags.from_import = True
			doc.insert(ignore_permissions=True)
			result = (doc.name, doc.marketing_campaign)
		self.objects[key] = result
		return result

	def match(self, title):
		"""The campaign whose code starts the channel's name: '2026q1-expo_search' -> 2026q1-expo."""
		head = (title or "").strip().lower().split(self.separator, 1)[0].strip()
		return head if head in self.codes else None

	def leaf(self, row):
		parent = None
		for object_type, prefix in LEVELS:
			ext = (row.get(f"{prefix}_id") or "").strip()
			title = (row.get(f"{prefix}_name") or "").strip()
			if not ext and not title:
				continue
			parent = self.object(object_type, ext or f"name:{title}", title, parent)
		return parent or (None, None)

	def save(self, row):
		date = getdate(row["date"])
		ad_object, campaign = self.leaf(row)
		key = {
			"date": date,
			"ad_account": self.account.name,
			"ad_object": ad_object,
			"placement": (row.get("placement") or "").strip().lower() or None,
			"source": self.source,
		}
		values = {
			f: (cint(row.get(f)) if f in ("impressions", "reach", "clicks") else flt(row.get(f)))
			for f in FIGURES
		}
		values.update(
			marketing_campaign=campaign,
			currency=row.get("currency") or self.account.currency,
			import_batch=self.batch,
		)
		name = frappe.db.get_value(
			"Marketing Performance", {k: v if v is not None else ("is", "not set") for k, v in key.items()}
		)
		if name:
			frappe.db.set_value("Marketing Performance", name, values)
		else:
			frappe.get_doc({"doctype": "Marketing Performance", **key, **values}).insert(
				ignore_permissions=True
			)
		return date


def campaign_tree(ad_object):
	"""The object and every object below it."""
	names, frontier = [ad_object], [ad_object]
	while frontier:
		frontier = frappe.get_all(
			"Marketing Ad Object", filters={"parent_object": ("in", frontier)}, pluck="name"
		)
		names += frontier
	return names


def apply_campaign(ad_object, campaign):
	"""After an object is matched by hand: the objects below it that were not matched by hand, and their figures."""
	tree = campaign_tree(ad_object)
	below = [n for n in tree[1:] if not frappe.db.get_value("Marketing Ad Object", n, "mapped_manually")]
	if below:
		frappe.db.set_value(
			"Marketing Ad Object",
			{"name": ("in", below)},
			"marketing_campaign",
			campaign,
			update_modified=False,
		)
	frappe.db.set_value(
		"Marketing Performance",
		{"ad_object": ("in", [ad_object, *below])},
		"marketing_campaign",
		campaign,
		update_modified=False,
	)


def check_unique(doc):
	other = frappe.db.get_value(
		"Marketing Ad Object",
		{
			"ad_account": doc.ad_account,
			"object_type": doc.object_type,
			"external_id": doc.external_id,
			"name": ("!=", doc.name),
		},
	)
	if other:
		frappe.throw(
			_("{0} {1} already exists for this ad account ({2})").format(
				_(doc.object_type), doc.external_id, other
			)
		)
