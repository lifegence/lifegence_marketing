# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lifegence_marketing import csv_import
from lifegence_marketing.performance import Saver


class MarketingImport(Document):
	def run(self):
		profile = frappe.get_doc("Marketing Import Profile", self.profile) if self.profile else None
		content = frappe.get_doc("File", {"file_url": self.file}).get_content()
		try:
			rows, messages = csv_import.read(
				content,
				encoding=profile.encoding if profile else "Auto",
				skip_rows=profile.skip_rows if profile else 0,
				date_format=profile.date_format if profile else None,
				profile_columns={c.target: c.source_column for c in profile.columns} if profile else None,
			)
		except ValueError as e:
			self.db_set({"status": "Failed", "messages": str(e)})
			return
		saver = Saver(self.ad_account, "CSV", self.name)
		dates = [saver.save(r) for r in rows]
		self.db_set(
			{
				"status": "Done",
				"rows_imported": len(rows),
				"rows_skipped": len(messages),
				"date_from": min(dates) if dates else None,
				"date_to": max(dates) if dates else None,
				"messages": "\n".join(messages[:200]) or _("Imported {0} rows").format(len(rows)),
			}
		)


@frappe.whitelist()
def start(name: str):
	doc = frappe.get_doc("Marketing Import", name)
	doc.check_permission("write")
	if doc.status == "Queued":
		frappe.throw(_("This import is already queued"))
	doc.db_set("status", "Queued")
	frappe.enqueue(run_import, queue="long", name=name, enqueue_after_commit=True)


def run_import(name):
	frappe.get_doc("Marketing Import", name).run()
