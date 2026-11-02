// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.query_reports["KPI Scorecard Summary"] = {
	filters: [
		{
			fieldname: "kpi_period",
			label: __("KPI Period"),
			fieldtype: "Link",
			options: "KPI Period",
			reqd: 1,
		},
		{
			fieldname: "kpi_role",
			label: __("KPI Role"),
			fieldtype: "Select",
			options: ["", "Application Engineer", "Sales Engineer", "Other"],
		},
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldtype === "Percent" && data && data[column.fieldname] != null) {
			const v = data[column.fieldname];
			const colour = v >= 100 ? "green" : v >= 80 ? "blue" : "red";
			value = `<span style="color: var(--${colour}-600)">${value}</span>`;
		}
		return value;
	},
};
