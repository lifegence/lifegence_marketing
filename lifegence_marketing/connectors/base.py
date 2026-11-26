# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""The contract a connector implements. All data crosses it as plain dicts.

Performance rows (fetch_performance) use the keys of lifegence_marketing.performance: date, campaign_id,
campaign_name, ad_group_id, ad_group_name, ad_id, ad_name, placement, impressions, reach, clicks, cost, conversions,
conversion_value, currency.

Leads (fetch_leads) are dicts with: external_id (unique on the channel), created (datetime), form_id, campaign_id,
ad_id, first_name, last_name, email, phone, company, and any other answers in "answers" ({question: value}).
"""

import frappe


class ConnectorError(Exception):
	"""A failure the user can act on; the message is shown in the log."""


class AuthError(ConnectorError):
	"""The connection has expired or was revoked: the ad account must be connected again."""


class MarketingConnector:
	key = None  # the hook key, for example "meta"
	label = None  # shown to users, for example "Meta Marketing API"
	channel = None  # the Marketing Channel this connector serves, for example "Meta"
	auth_type = "oauth"  # "oauth" (Connected App) or "api_key" (the ad account's API Key)
	supports_leads = False

	# Credentials ------------------------------------------------------------

	def access_token(self, account):
		"""The token for the ad account: its Connected App token (OAuth) or its API key."""
		if self.auth_type == "api_key":
			key = account.get_password("api_key", raise_exception=False)
			if not key:
				raise AuthError(frappe._("The ad account has no API key"))
			return key
		if not account.connected_app:
			raise AuthError(frappe._("The ad account is not connected (set a Connected App)"))
		user = account.token_user or frappe.session.user
		token = frappe.get_doc("Connected App", account.connected_app).get_active_token(user)
		if not token:
			raise AuthError(
				frappe._("No valid token of {0} for {1}; connect again").format(user, account.connected_app)
			)
		return token.get_password("access_token")

	# What a connector implements ----------------------------------------------

	def test_connection(self, account):
		"""Raise ConnectorError (or AuthError) if the account cannot be read; return a short description otherwise."""
		raise NotImplementedError

	def fetch_performance(self, account, date_from, date_to):
		"""Daily rows for the period (both dates included), as an iterable of dicts."""
		raise NotImplementedError

	def fetch_leads(self, account, since):
		"""Leads created after `since` (a datetime or None), as an iterable of dicts. Only if supports_leads."""
		return []
