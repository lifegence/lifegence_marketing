# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

import frappe
from frappe.model.document import Document

from lifegence_marketing.performance import apply_campaign, check_unique


class MarketingAdObject(Document):
	def validate(self):
		check_unique(self)
		if not self.is_new() and not self.flags.from_import and self.has_value_changed("marketing_campaign"):
			self.mapped_manually = 1 if self.marketing_campaign else 0

	def on_update(self):
		if not self.flags.from_import and self.has_value_changed("marketing_campaign"):
			apply_campaign(self.name, self.marketing_campaign)
