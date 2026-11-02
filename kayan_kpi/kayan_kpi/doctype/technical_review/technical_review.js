// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("Technical Review", {
	setup(frm) {
		frm.set_query("quotation", () => ({ filters: { docstatus: 1 } }));
	},
});
