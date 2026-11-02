// Copyright (c) 2026, Nest Software Development and contributors
// For license information, please see license.txt

frappe.query_reports["KPI Evidence"] = {
	filters: [
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee", reqd: 1 },
		{
			fieldname: "kpi_period",
			label: __("KPI Period"),
			fieldtype: "Link",
			options: "KPI Period",
			reqd: 1,
		},
		{
			fieldname: "metric",
			label: __("KPI"),
			fieldtype: "Select",
			reqd: 1,
			options: [
				"Quote Turnaround (SLA)",
				"Selection Accuracy",
				"Standards Compliance",
				"Client Query Service",
				"Quotation Win Rate",
				"Paperwork Complete",
				"Sales Target Achievement",
				"Quotation Hit Rate",
				"New Clients",
				"Sales Cycle Time",
				"Repeat Client Revenue",
				"Records Up To Date",
				"Competitor Study",
				"Margin Bonus",
			],
		},
		{
			fieldname: "kpi_role",
			label: __("KPI Role"),
			fieldtype: "Select",
			options: ["", "Application Engineer", "Sales Engineer"],
			description: __("Leave empty to use the employee's KPI Template"),
		},
	],
};
