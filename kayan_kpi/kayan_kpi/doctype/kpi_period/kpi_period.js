// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("KPI Period", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Open") return;
		frm.add_custom_button(__("Create Scorecards"), () => {
			frappe.call({
				method: "kayan_kpi.api.create_scorecards",
				args: { period: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating and calculating scorecards..."),
				callback: (r) => {
					const { created, existing } = r.message;
					frappe.msgprint(
						__("{0} scorecards created, {1} already existed.", [created.length, existing.length])
					);
				},
			});
		});
		frm.add_custom_button(__("Scorecards"), () =>
			frappe.set_route("List", "KPI Scorecard", { kpi_period: frm.doc.name })
		, __("View"));
		frm.add_custom_button(__("Summary"), () =>
			frappe.set_route("query-report", "KPI Scorecard Summary", { kpi_period: frm.doc.name })
		, __("View"));
	},
});
