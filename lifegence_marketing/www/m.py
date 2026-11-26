# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Short URL of a tracking link: /m/<code> counts the click and redirects to the tracking URL."""

import frappe

from lifegence_marketing.marketing.doctype.marketing_tracking_link.marketing_tracking_link import resolve

no_cache = 1


def get_context(context):
	url = resolve(frappe.form_dict.get("code") or "")
	if not url:
		raise frappe.PageDoesNotExistError
	frappe.db.commit()  # the click count; the redirect below ends the request
	frappe.local.flags.redirect_location = url
	raise frappe.Redirect(302)  # not 301: a cached permanent redirect would skip the click count
