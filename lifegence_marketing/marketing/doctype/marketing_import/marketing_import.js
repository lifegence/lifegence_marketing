// Copyright (c) 2026, Lifegence Corporation
// License: Apache-2.0. See license.txt

frappe.ui.form.on("Marketing Import", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.file && frm.doc.status !== "Queued") {
			frm.page.set_primary_action(__("Import"), () =>
				frappe
					.call(
						"lifegence_marketing.marketing.doctype.marketing_import.marketing_import.start",
						{ name: frm.doc.name }
					)
					.then(() => {
						frappe.show_alert({ message: __("Import queued"), indicator: "blue" });
						frm.reload_doc();
					})
			);
		}
	},
});
