# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from kayan_kpi.kpi.common import SALES
from kayan_kpi.kpi.engine import make_context
from kayan_kpi.kpi.metrics.shared import margin_bonus
from kayan_kpi.permissions import visible_employees


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.kpi_period:
        return columns(), []

    employees = (
        [filters.employee]
        if filters.employee
        else frappe.get_all(
            "Employee",
            filters={
                "status": "Active",
                "kpi_template": [
                    "in",
                    frappe.get_all("KPI Template", filters={"kpi_role": SALES}, pluck="name") or [""],
                ],
            },
            pluck="name",
        )
    )
    visible = visible_employees(frappe.session.user)
    if visible is not None:
        employees = [e for e in employees if e in visible]

    data = []
    total_points = 0.0
    for employee in employees:
        name = frappe.db.get_value("Employee", employee, "employee_name")
        result = margin_bonus(make_context(employee, filters.kpi_period, SALES))
        total_points += flt(result.actual)
        for r in result.rows:
            if filters.qualified_only and not flt(r["result"]):
                continue
            data.append(
                {
                    "employee": employee,
                    "employee_name": name,
                    "reference_doctype": r["doctype"],
                    "reference_name": r["name"],
                    "date": r["date"],
                    "customer": r["party"],
                    "credit": r["credit"],
                    "margin": r["value"],
                    "points": r["result"],
                    "note": r["note"],
                }
            )
    summary = [{"label": _("Total Bonus Points"), "value": round(total_points, 2), "datatype": "Float"}]
    return columns(), data, None, None, summary


def columns():
    return [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 110,
        },
        {"label": _("Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {
            "label": _("Type"),
            "fieldname": "reference_doctype",
            "fieldtype": "Link",
            "options": "DocType",
            "width": 110,
        },
        {
            "label": _("Document"),
            "fieldname": "reference_name",
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 160,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Data", "width": 170},
        {"label": _("Credit"), "fieldname": "credit", "fieldtype": "Float", "width": 70},
        {"label": _("Margin %"), "fieldname": "margin", "fieldtype": "Percent", "width": 100},
        {"label": _("Points"), "fieldname": "points", "fieldtype": "Float", "width": 100},
        {"label": _("Note"), "fieldname": "note", "fieldtype": "Data", "width": 200},
    ]
