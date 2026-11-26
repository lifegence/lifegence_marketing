# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Where a visitor came from, and writing it on the lead they become.

1. after_request: a website request whose URL carries UTM parameters or click IDs (gclid, fbclid, ...) sets the
   first-party cookie lm_attr: the first touch (kept) and the last touch (replaced), with the click IDs. It is set by
   the server, so it works without JavaScript; with "Record Only With Consent", only when the consent cookie exists.
2. Lead / CRM Lead before_insert: the last touch fills utm_source / utm_medium / utm_campaign, but only with values
   that already exist as UTM Source / Medium / Campaign (anyone can put anything in a URL; unknown values are kept
   only in the attribution record, so they do not create master records).
3. after_insert: a Marketing Attribution keeps both touches, the click IDs and the matching campaigns. A Frappe CRM
   lead from a Meta lead form (facebook_form_id) gets its campaign from Marketing Lead Form Map.
"""

import base64
import datetime
import json
import time
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import cint, now_datetime

COOKIE = "lm_attr"
UTM = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
SKIP_PREFIXES = ("/api/", "/app/", "/desk", "/assets/", "/files/", "/private/", "/socket.io")
LEAD_DOCTYPES = ("Lead", "CRM Lead")


def settings():
	s = frappe.get_cached_doc("Marketing Settings")
	params = [p.strip() for p in (s.click_id_params or "").splitlines() if p.strip()]
	return frappe._dict(
		days=cint(s.attribution_days) or 90,
		click_ids=params,
		consent=bool(s.cookie_consent_required),
		consent_cookie=(s.consent_cookie_name or "").strip(),
	)


def encode(data):
	return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()


def decode(value):
	try:
		data = json.loads(base64.urlsafe_b64decode((value or "").encode()).decode())
		return data if isinstance(data, dict) else {}
	except Exception:
		return {}


def touch_from(args, path, click_ids):
	touch = {k[4:]: str(args.get(k))[:140] for k in UTM if args.get(k)}
	clicks = {k: str(args.get(k))[:255] for k in click_ids if args.get(k)}
	if not touch and not clicks:
		return None, None
	touch["landing"] = (path or "/")[:140]
	touch["at"] = int(time.time())
	return touch, clicks


def after_request(response, request):
	"""Set lm_attr when a website page is opened with UTM parameters or click IDs."""
	if request.method != "GET" or request.path.startswith(SKIP_PREFIXES) or not request.args:
		return
	s = settings()
	if not (set(request.args) & (set(UTM) | set(s.click_ids))):
		return
	if s.consent and not (s.consent_cookie and request.cookies.get(s.consent_cookie)):
		return
	touch, clicks = touch_from(request.args, request.path, s.click_ids)
	if not touch:
		return
	data = decode(request.cookies.get(COOKIE))
	data.setdefault("f", touch)
	data["l"] = touch
	data["c"] = {**(data.get("c") or {}), **clicks}
	response.set_cookie(
		COOKIE,
		encode(data),
		max_age=s.days * 86400,
		secure=request.scheme == "https",
		httponly=True,
		samesite="Lax",
	)


def current():
	"""The visitor's lm_attr of the current request ({} outside a request or without the cookie)."""
	request = getattr(frappe.local, "request", None)
	cookies = getattr(request, "cookies", None) or {}
	return decode(cookies.get(COOKIE))


def existing(doctype, value):
	"""The name of a UTM record matching the value (by name or slug), or None."""
	if not value:
		return None
	return frappe.db.get_value(doctype, value, "name") or frappe.db.get_value(
		doctype, {"slug": value}, "name"
	)


def campaign_of(value):
	utm = existing("UTM Campaign", value)
	return frappe.db.get_value("Marketing Campaign", {"utm_campaign": utm}, "name") if utm else None


def before_insert_lead(doc, method=None):
	last = current().get("l") or {}
	for field, doctype in (
		("utm_source", "UTM Source"),
		("utm_medium", "UTM Medium"),
		("utm_campaign", "UTM Campaign"),
	):
		if doc.meta.has_field(field) and not doc.get(field):
			doc.set(field, existing(doctype, last.get(field[4:])))
	if doc.meta.has_field("marketing_campaign") and not doc.get("marketing_campaign"):
		form = doc.get("facebook_form_id")
		doc.marketing_campaign = (form and lead_form_campaign(form)) or campaign_of(doc.get("utm_campaign"))


def lead_form_campaign(form_id):
	return frappe.db.get_value("Marketing Lead Form Map", {"form_id": form_id}, "marketing_campaign")


def after_insert_lead(doc, method=None):
	data = current()
	form = doc.get("facebook_form_id")
	if not data and not form:
		return
	first, last = data.get("f") or {}, data.get("l") or {}
	row = {"doctype": "Marketing Attribution", "reference_doctype": doc.doctype, "reference_name": doc.name}
	for prefix, touch in (("first", first), ("last", last)):
		for key in ("source", "medium", "campaign", "content", "term", "landing"):
			row[f"{prefix}_{key}"] = touch.get(key)
		row[f"{prefix}_at"] = local_time(touch.get("at"))
		row[f"{prefix}_campaign_link"] = campaign_of(touch.get("campaign"))
	row["click_ids"] = json.dumps(data.get("c") or {}) if data.get("c") else None
	if form:
		row["lead_form"] = form
		row["last_campaign_link"] = row["last_campaign_link"] or lead_form_campaign(form)
		row["first_campaign_link"] = row["first_campaign_link"] or row["last_campaign_link"]
	row["recorded_on"] = now_datetime()
	frappe.get_doc(row).insert(ignore_permissions=True)


def local_time(timestamp):
	if not timestamp:
		return None
	tz = ZoneInfo(frappe.utils.get_system_timezone())
	return datetime.datetime.fromtimestamp(int(timestamp), tz=tz).replace(tzinfo=None)


def before_insert_deal(doc, method=None):
	"""A Frappe CRM deal takes the UTM fields and campaign of its lead."""
	if not doc.get("lead"):
		return
	fields = [
		f for f in ("utm_source", "utm_medium", "utm_campaign", "marketing_campaign") if doc.meta.has_field(f)
	]
	values = frappe.db.get_value("CRM Lead", doc.lead, fields, as_dict=True) or {}
	for f in fields:
		if not doc.get(f) and values.get(f):
			doc.set(f, values[f])
