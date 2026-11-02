// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.ui.form.on("KPI Scorecard", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Recalculate"), () => {
				frappe.call({
					method: "kayan_kpi.api.recalculate_scorecard",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Calculating KPIs..."),
					callback: () => frm.reload_doc(),
				});
			});
		}
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Evidence"),
				() => frappe.set_route("query-report", "KPI Evidence", {
					employee: frm.doc.employee,
					kpi_period: frm.doc.kpi_period,
					kpi_role: frm.doc.kpi_role,
				}),
				__("View")
			);
		}
		if (frm.doc.last_calculated_on) {
			frm.set_intro(
				__("Calculated {0}. Total score {1}%, using {2}% of the weight that had data.", [
					frappe.datetime.prettyDate(frm.doc.last_calculated_on),
					format_number(frm.doc.total_score, null, 1),
					format_number(frm.doc.scored_weight, null, 0),
				]),
				frm.doc.total_score >= 100 ? "green" : frm.doc.total_score >= 80 ? "blue" : "orange"
			);
		}
	},
});

frappe.ui.form.on("KPI Scorecard Item", {
	view_evidence(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.set_route("query-report", "KPI Evidence", {
			employee: frm.doc.employee,
			kpi_period: frm.doc.kpi_period,
			kpi_role: frm.doc.kpi_role,
			metric: row.metric,
		});
	},
});
