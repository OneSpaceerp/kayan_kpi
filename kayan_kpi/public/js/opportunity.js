// Kayan KPI: ask for the real date of a stage change, and quick links to KPI records

frappe.ui.form.on("Opportunity", {
	sales_stage(frm) {
		if (!frm.is_new() && !frm.doc.kpi_event_on) {
			frappe.show_alert({
				message: __("Fill KPI Tracking → Change Happened On with the date this stage was reached."),
				indicator: "orange",
			});
		}
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Technical Query"), () =>
			frappe.new_doc("Technical Query", {
				reference_doctype: "Opportunity",
				reference_name: frm.doc.name,
				employee: frm.doc.kpi_application_engineer,
				customer: frm.doc.opportunity_from === "Customer" ? frm.doc.party_name : undefined,
			})
		, __("Create"));
	},
});
