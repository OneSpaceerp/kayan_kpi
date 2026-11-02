// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.query_reports["Margin Bonus"] = {
	filters: [
		{
			fieldname: "kpi_period",
			label: __("KPI Period"),
			fieldtype: "Link",
			options: "KPI Period",
			reqd: 1,
		},
		{ fieldname: "employee", label: __("Sales Engineer"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "qualified_only", label: __("Bonus Deals Only"), fieldtype: "Check", default: 1 },
	],
};
