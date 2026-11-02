// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("Kayan KPI Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Backfill Existing Quotations"), () => {
			frappe.confirm(
				__("Fill the KPI fields and engineers on submitted quotations that do not have them yet?"),
				() =>
					frappe.call({
						method: "kayan_kpi.api.backfill_quotations",
						callback: (r) => frappe.show_alert({ message: r.message, indicator: "green" }),
					})
			);
		});
	},
});
