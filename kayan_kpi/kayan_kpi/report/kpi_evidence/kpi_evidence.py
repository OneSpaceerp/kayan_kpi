# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

"""The documents behind one KPI: what was counted, how much credit, and the result."""

import frappe
from frappe import _

from kayan_kpi.kpi.engine import evidence_for
from kayan_kpi.permissions import visible_employees


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not (filters.employee and filters.kpi_period and filters.metric):
        return columns(), [], _("Choose an employee, a period and a KPI.")

    visible = visible_employees(frappe.session.user)
    if visible is not None and filters.employee not in visible:
        frappe.throw(
            _("You can only see the KPI evidence of yourself and your team."), frappe.PermissionError
        )

    result = evidence_for(filters.employee, filters.kpi_period, filters.metric, filters.kpi_role)
    data = [
        {
            "reference_doctype": r["doctype"],
            "reference_name": r["name"],
            "date": r["date"],
            "party": r["party"],
            "credit": r["credit"],
            "value": r["value"],
            "result": r["result"],
            "note": r["note"],
        }
        for r in result.rows
    ]
    actual = "-" if result.actual is None else round(result.actual, 2)
    message = f"<b>{_('Actual')}: {actual}</b> &nbsp; {frappe.utils.escape_html(result.details or '')}"
    summary = [
        {"label": _("Actual"), "value": actual, "datatype": "Data"},
        {"label": _("Counted / Achieved"), "value": round(result.numerator or 0, 2), "datatype": "Float"},
        {"label": _("Out Of"), "value": round(result.denominator or 0, 2), "datatype": "Float"},
    ]
    return columns(), data, message, None, summary


def columns():
    return [
        {
            "label": _("Type"),
            "fieldname": "reference_doctype",
            "fieldtype": "Link",
            "options": "DocType",
            "width": 140,
        },
        {
            "label": _("Document"),
            "fieldname": "reference_name",
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 180,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Data", "width": 150},
        {"label": _("Customer / Reference"), "fieldname": "party", "fieldtype": "Data", "width": 180},
        {"label": _("Credit"), "fieldname": "credit", "fieldtype": "Float", "width": 80},
        {"label": _("Value"), "fieldname": "value", "fieldtype": "Data", "width": 110},
        {"label": _("Result"), "fieldname": "result", "fieldtype": "Data", "width": 130},
        {"label": _("Note"), "fieldname": "note", "fieldtype": "Data", "width": 260},
    ]
