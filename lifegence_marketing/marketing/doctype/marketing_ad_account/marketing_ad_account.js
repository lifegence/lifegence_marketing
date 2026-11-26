// Copyright (c) 2026, Lifegence Corporation
// License: Apache-2.0. See license.txt

const SYNC_API = "lifegence_marketing.connectors.sync.";

frappe.ui.form.on("Marketing Ad Account", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Test Connection"), () =>
			frappe.call(SYNC_API + "test_connection", { name: frm.doc.name }).then((r) => {
				const res = r.message || {};
				frappe.msgprint({ message: res.message || "", indicator: res.ok ? "green" : "red", title: res.ok ? __("Connected") : __("Not Connected") });
			})
		);
		frm.add_custom_button(__("Import Now"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Import Now"),
				fields: [
					{ fieldname: "date_from", fieldtype: "Date", label: __("From Date"), description: __("Empty: the usual period") },
					{ fieldname: "date_to", fieldtype: "Date", label: __("To Date") },
				],
				primary_action_label: __("Import"),
				primary_action(values) {
					frappe.call(SYNC_API + "sync_now", { name: frm.doc.name, ...values }).then(() => {
						d.hide();
						frappe.show_alert({ message: __("Import queued"), indicator: "blue" });
					});
				},
			});
			d.show();
		});
		frm.add_custom_button(__("Import Log"), () => frappe.set_route("List", "Marketing Sync Log", { ad_account: frm.doc.name }));
	},
});
