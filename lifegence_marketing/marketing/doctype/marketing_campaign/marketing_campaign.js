// Copyright (c) 2026, Lifegence Corporation
// License: Apache-2.0. See license.txt

frappe.ui.form.on("Marketing Campaign", {
	refresh(frm) {
		const ringi = (frm.doc.__onload || {}).ringi;
		if (frm.is_new() || !ringi || !ringi.required) return;
		if (ringi.decided) {
			frm.dashboard.add_comment(__("Approved by ringi {0}", [ringi.decided]), "green", true);
			return;
		}
		if (["Planned", "Pending Approval"].includes(frm.doc.status)) {
			frm.dashboard.add_comment(__("A decided ringi is needed before this campaign becomes Active."), "orange", true);
			frm.add_custom_button(__("Create Ringi"), () =>
				frappe.new_doc("Ringi", {
					title: frm.doc.campaign_name,
					ringi_type: ringi.type || undefined,
					amount: frm.doc.total_budget,
					currency: frm.doc.currency,
					company: frm.doc.company || undefined,
					reference_doctype: "Marketing Campaign",
					reference_name: frm.doc.name,
				})
			);
		}
	},
});
