# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})
    conditions = {"kpi_period": filters.kpi_period, "docstatus": ["<", 2]}
    if filters.kpi_role:
        conditions["kpi_role"] = filters.kpi_role
    if filters.department:
        conditions["department"] = filters.department

    scorecards = frappe.get_list(
        "KPI Scorecard",
        filters=conditions,
        fields=[
            "name",
            "employee",
            "employee_name",
            "department",
            "kpi_role",
            "total_score",
            "bonus_points",
            "status",
        ],
        order_by="total_score desc",
        limit_page_length=0,
    )
    items = frappe.get_all(
        "KPI Scorecard Item",
        filters={"parent": ["in", [s.name for s in scorecards] or [""]], "parenttype": "KPI Scorecard"},
        fields=["parent", "goal", "achievement_percent", "has_data", "override", "idx"],
        order_by="idx asc",
        limit_page_length=0,
    )

    goals = []
    by_card = {}
    for item in items:
        if item.goal not in goals:
            goals.append(item.goal)
        by_card.setdefault(item.parent, {})[item.goal] = (
            item.achievement_percent if (item.has_data or item.override) else None
        )

    columns = [
        {
            "label": _("Scorecard"),
            "fieldname": "scorecard",
            "fieldtype": "Link",
            "options": "KPI Scorecard",
            "width": 150,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {"label": _("Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 170},
        {"label": _("Role"), "fieldname": "kpi_role", "fieldtype": "Data", "width": 150},
    ]
    for i, goal in enumerate(goals):
        columns.append({"label": goal, "fieldname": f"kpi_{i}", "fieldtype": "Percent", "width": 130})
    columns += [
        {"label": _("Total Score"), "fieldname": "total_score", "fieldtype": "Percent", "width": 110},
        {"label": _("Bonus Points"), "fieldname": "bonus_points", "fieldtype": "Float", "width": 110},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

    data = []
    for s in scorecards:
        row = {
            "scorecard": s.name,
            "employee": s.employee,
            "employee_name": s.employee_name,
            "kpi_role": s.kpi_role,
            "total_score": s.total_score,
            "bonus_points": s.bonus_points,
            "status": s.status,
        }
        for i, goal in enumerate(goals):
            row[f"kpi_{i}"] = by_card.get(s.name, {}).get(goal)
        data.append(row)

    chart = {
        "data": {
            "labels": [d["employee_name"] for d in data],
            "datasets": [{"name": _("Total Score"), "values": [flt(d["total_score"]) for d in data]}],
        },
        "type": "bar",
        "colors": ["#B71C1C"],
    }
    summary = []
    if data:
        avg = sum(flt(d["total_score"]) for d in data) / len(data)
        summary = [
            {"label": _("Scorecards"), "value": len(data), "datatype": "Int"},
            {
                "label": _("Average Score"),
                "value": round(avg, 1),
                "datatype": "Percent",
                "indicator": "Green" if avg >= 100 else "Blue" if avg >= 80 else "Orange",
            },
            {
                "label": _("Approved"),
                "value": sum(1 for d in data if d["status"] == "Approved"),
                "datatype": "Int",
            },
        ]
    return columns, data, None, chart, summary
