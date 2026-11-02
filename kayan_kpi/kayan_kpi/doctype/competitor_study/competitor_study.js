// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("Competitor Study", {
	setup(frm) {
		frm.set_query("quotation", () => ({ filters: { docstatus: ["<", 2] } }));
	},
	refresh(frm) {
		if (frm.doc.study_score !== undefined && !frm.is_new()) {
			frm.dashboard.set_headline(
				__("Study score {0}%", [format_number(frm.doc.study_score, null, 0)]),
				frm.doc.study_score >= 80 ? "green" : "orange"
			);
		}
	},
});
