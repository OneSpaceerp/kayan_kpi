// Kayan KPI: turnaround status and KPI shortcuts on the Quotation form

frappe.ui.form.on("Quotation", {
	setup(frm) {
		frm.set_query("employee", "kpi_engineers", () => ({ filters: { status: "Active" } }));
	},
	refresh(frm) {
		frm.trigger("show_sla");
		if (frm.doc.docstatus !== 1) return;
		if (frappe.user.has_role(["KPI Manager", "System Manager"])) {
			frm.add_custom_button(
				__("Technical Review"),
				() => frappe.new_doc("Technical Review", { quotation: frm.doc.name }),
				__("Create")
			);
		}
		frm.add_custom_button(
			__("Competitor Study"),
			() => frappe.new_doc("Competitor Study", { quotation: frm.doc.name, opportunity: frm.doc.opportunity }),
			__("Create")
		);
	},
	show_sla(frm) {
		if (!frm.doc.kpi_due_on) return;
		const hours = format_number(frm.doc.kpi_tat_hours, null, 1);
		if (frm.doc.docstatus === 1) {
			const on_time = frm.doc.kpi_within_sla;
			frm.dashboard.add_comment(
				on_time
					? __("KPI: ready within the SLA ({0} working hours)", [hours])
					: __("KPI: ready after the SLA due time ({0} working hours)", [hours]),
				on_time ? "green" : "red",
				true
			);
		} else if (frm.doc.docstatus === 0) {
			const overdue = frappe.datetime.str_to_obj(frm.doc.kpi_due_on) < new Date();
			frm.dashboard.add_comment(
				__("KPI: ready to send by {0}", [frappe.datetime.str_to_user(frm.doc.kpi_due_on)]),
				overdue ? "red" : "blue",
				true
			);
		}
	},
});
