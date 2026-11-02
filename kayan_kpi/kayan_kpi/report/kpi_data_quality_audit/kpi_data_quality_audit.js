// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.query_reports["KPI Data Quality Audit"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.get_today() },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "severity" && data) {
			const colour = { High: "red", Medium: "orange", Low: "blue" }[data.severity];
			value = `<span class="indicator-pill ${colour}">${value}</span>`;
		}
		return value;
	},
};
