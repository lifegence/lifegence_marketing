# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""A destination URL with UTM parameters, a short URL (/m/<name>) that counts clicks, and a QR code."""

import re
from io import BytesIO
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

UTM_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


def clean(value):
	return re.sub(r"\s+", "_", (value or "").strip().lower())


class MarketingTrackingLink(Document):
	def validate(self):
		parts = urlsplit((self.base_url or "").strip())
		if parts.scheme not in ("http", "https") or not parts.netloc:
			frappe.throw(_("The destination must be an http or https URL"))
		channel = frappe.get_cached_doc("Marketing Channel", self.channel)
		self.utm_source = clean(self.utm_source or channel.utm_source or channel.channel_name)
		self.utm_medium = clean(self.utm_medium or channel.utm_medium or channel.channel_type)
		self.utm_campaign = (
			frappe.db.get_value("Marketing Campaign", self.campaign, "utm_campaign") or self.campaign
		)
		self.utm_content = clean(self.utm_content)
		self.utm_term = clean(self.utm_term)
		query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in UTM_FIELDS]
		query += [(k, self.get(k)) for k in UTM_FIELDS if self.get(k)]
		self.full_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

	def on_update(self):
		short = get_url(f"/m/{self.name}")
		if self.short_url != short:
			self.db_set("short_url", short, update_modified=False)
		if not self.qr_code:
			self.db_set("qr_code", make_qr(self, short), update_modified=False)


def make_qr(doc, url):
	import pyqrcode

	buf = BytesIO()
	pyqrcode.create(url).svg(buf, scale=4, quiet_zone=2)
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"qr-{doc.name}.svg",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"attached_to_field": "qr_code",
			"is_private": 0,
			"content": buf.getvalue(),
		}
	).insert(ignore_permissions=True)
	return file.file_url


def resolve(code):
	"""The tracking URL of a short code, counting the click; None when unknown or disabled."""
	row = frappe.db.get_value("Marketing Tracking Link", code, ["full_url", "disabled"], as_dict=True)
	if not row or row.disabled:
		return None
	frappe.db.sql("update `tabMarketing Tracking Link` set clicks = clicks + 1 where name = %s", code)
	return row.full_url
