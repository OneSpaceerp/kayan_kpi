// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.query_reports["Quotation Turnaround"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.get_today() },
		{ fieldname: "employee", label: __("Engineer"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "status", label: __("SLA"), fieldtype: "Select", options: ["", "On Time", "Late"] },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "sla" && data) {
			value = `<span class="indicator-pill ${data.kpi_within_sla ? "green" : "red"}">${value}</span>`;
		}
		return value;
	},
};
