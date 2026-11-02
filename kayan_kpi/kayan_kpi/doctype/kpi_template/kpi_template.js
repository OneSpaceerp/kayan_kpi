// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("KPI Template", {
	refresh(frm) {
		frm.trigger("show_weight");
	},
	show_weight(frm) {
		const total = (frm.doc.items || []).reduce((sum, r) => sum + flt(r.weight), 0);
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(
			__("Total weight: {0}%", [format_number(total, null, 2)]),
			Math.abs(total - 100) < 0.001 ? "green" : "red"
		);
	},
});

frappe.ui.form.on("KPI Template Item", {
	weight: (frm) => frm.trigger("show_weight"),
	items_remove: (frm) => frm.trigger("show_weight"),
});
