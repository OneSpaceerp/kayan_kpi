// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("Technical Query", {
	setup(frm) {
		frm.set_query("reference_doctype", () => ({
			filters: { name: ["in", ["Opportunity", "Quotation", "CRM Deal", "Lead", "Customer"]] },
		}));
	},
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.first_reply_on) {
			frm.add_custom_button(__("Mark as Replied"), () =>
				frappe.call({
					method: "kayan_kpi.api.mark_query_replied",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc(),
				})
			);
		}
		if (frm.doc.first_reply_on) {
			frm.dashboard.set_headline(
				__("Replied in {0} hours", [format_number(frm.doc.reply_hours, null, 1)]),
				frm.doc.replied_on_time ? "green" : "red"
			);
		}
	},
});
