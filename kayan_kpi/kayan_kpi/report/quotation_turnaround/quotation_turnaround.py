# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, get_datetime


def execute(filters=None):
    filters = frappe._dict(filters or {})
    conditions = {
        "docstatus": 1,
        "kpi_ready_on": [
            "between",
            [get_datetime(f"{filters.from_date} 00:00:00"), get_datetime(f"{filters.to_date} 23:59:59")],
        ],
    }
    if filters.company:
        conditions["company"] = filters.company
    if filters.employee:
        conditions["name"] = [
            "in",
            frappe.get_all(
                "KPI Quotation Engineer",
                filters={"parenttype": "Quotation", "employee": filters.employee},
                pluck="parent",
            )
            or [""],
        ]
    if filters.status == "Late":
        conditions["kpi_within_sla"] = 0
    elif filters.status == "On Time":
        conditions["kpi_within_sla"] = 1

    quotations = frappe.get_list(
        "Quotation",
        filters=conditions,
        fields=[
            "name",
            "customer_name",
            "kpi_inquiry_complexity",
            "kpi_request_received_on",
            "kpi_request_source",
            "kpi_due_on",
            "kpi_ready_on",
            "kpi_tat_hours",
            "kpi_within_sla",
            "status",
            "base_net_total",
        ],
        order_by="kpi_ready_on desc",
        limit_page_length=0,
    )
    engineers = {}
    for row in frappe.get_all(
        "KPI Quotation Engineer",
        filters={"parenttype": "Quotation", "parent": ["in", [q.name for q in quotations] or [""]]},
        fields=["parent", "employee_name", "kpi_role", "is_primary"],
        order_by="is_primary desc, idx asc",
    ):
        engineers.setdefault(row.parent, []).append(row.employee_name)

    data = []
    for q in quotations:
        q.engineers = ", ".join(engineers.get(q.name, []))
        q.sla = _("On Time") if cint(q.kpi_within_sla) else _("Late")
        data.append(q)

    on_time = sum(1 for q in data if cint(q.kpi_within_sla))
    chart = {
        "data": {
            "labels": [_("On Time"), _("Late")],
            "datasets": [{"values": [on_time, len(data) - on_time]}],
        },
        "type": "donut",
        "colors": ["#2E7D32", "#B71C1C"],
    }
    summary = [
        {"label": _("Quotations"), "value": len(data), "datatype": "Int"},
        {"label": _("On Time"), "value": on_time, "datatype": "Int", "indicator": "Green"},
        {"label": _("Late"), "value": len(data) - on_time, "datatype": "Int", "indicator": "Red"},
        {
            "label": _("On-time Rate"),
            "value": round(on_time / len(data) * 100, 1) if data else 0,
            "datatype": "Percent",
        },
    ]
    return columns(), data, None, chart, summary


def columns():
    return [
        {
            "label": _("Quotation"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Quotation",
            "width": 150,
        },
        {"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 170},
        {"label": _("Engineers"), "fieldname": "engineers", "fieldtype": "Data", "width": 180},
        {"label": _("Inquiry"), "fieldname": "kpi_inquiry_complexity", "fieldtype": "Data", "width": 90},
        {
            "label": _("Request Received"),
            "fieldname": "kpi_request_received_on",
            "fieldtype": "Datetime",
            "width": 160,
        },
        {"label": _("Due"), "fieldname": "kpi_due_on", "fieldtype": "Datetime", "width": 160},
        {"label": _("Ready"), "fieldname": "kpi_ready_on", "fieldtype": "Datetime", "width": 160},
        {"label": _("Working Hours"), "fieldname": "kpi_tat_hours", "fieldtype": "Float", "width": 110},
        {"label": _("SLA"), "fieldname": "sla", "fieldtype": "Data", "width": 90},
        {
            "label": _("Request Time From"),
            "fieldname": "kpi_request_source",
            "fieldtype": "Data",
            "width": 200,
        },
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]
