# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

"""Records that would make a KPI wrong or incomplete. Fix these before approving scorecards."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, nowdate

from kayan_kpi.kpi.common import get_settings


def execute(filters=None):
    filters = frappe._dict(filters or {})
    start = get_datetime(f"{filters.from_date} 00:00:00")
    end = get_datetime(f"{filters.to_date} 23:59:59")
    settings = get_settings()
    company = {"company": filters.company} if filters.company else {}
    data = []

    def add(issue, doctype, name, when=None, details=None, severity="High"):
        data.append(
            {
                "severity": severity,
                "issue": issue,
                "reference_doctype": doctype,
                "reference_name": name,
                "date": when,
                "details": details,
            }
        )

    # Quotations
    submitted = frappe.get_all(
        "Quotation",
        filters={
            "docstatus": 1,
            "transaction_date": ["between", [filters.from_date, filters.to_date]],
            **company,
        },
        fields=["name", "transaction_date", "opportunity", "kpi_request_source", "kpi_crm_deal"],
        limit_page_length=0,
    )
    with_engineer = set(
        frappe.get_all(
            "KPI Quotation Engineer",
            filters={"parenttype": "Quotation", "parent": ["in", [q.name for q in submitted] or [""]]},
            pluck="parent",
        )
    )
    for q in submitted:
        if q.name not in with_engineer:
            add(
                _("Quotation has no KPI engineer"),
                "Quotation",
                q.name,
                q.transaction_date,
                _("Nobody is credited for this quotation."),
            )
        if (q.kpi_request_source or "").startswith("Quotation created"):
            add(
                _("No client request time"),
                "Quotation",
                q.name,
                q.transaction_date,
                _("Turnaround is measured from the quotation's creation."),
                "Medium",
            )
        if not q.opportunity and not q.kpi_crm_deal:
            add(
                _("Quotation not linked to an Opportunity or CRM Deal"),
                "Quotation",
                q.name,
                q.transaction_date,
                _("Request time and first contact cannot be traced."),
                "Medium",
            )

    stale = add_days(nowdate(), -cint(settings.draft_age_days or 7))
    for q in frappe.get_all(
        "Quotation",
        filters={"docstatus": 0, "creation": ["<", get_datetime(f"{stale} 00:00:00")], **company},
        fields=["name", "creation", "owner"],
        limit_page_length=0,
    ):
        add(
            _("Draft quotation older than {0} days").format(settings.draft_age_days),
            "Quotation",
            q.name,
            q.creation,
            _("Created by {0}").format(q.owner),
            "Medium",
        )

    # Sales Orders
    orders = frappe.get_all(
        "Sales Order",
        filters={
            "docstatus": 1,
            "transaction_date": ["between", [filters.from_date, filters.to_date]],
            **company,
        },
        fields=["name", "transaction_date", "po_no", "po_date"],
        limit_page_length=0,
    )
    names = [o.name for o in orders] or [""]
    with_team = set(
        frappe.get_all(
            "Sales Team", filters={"parenttype": "Sales Order", "parent": ["in", names]}, pluck="parent"
        )
    )
    from_quote = set(
        frappe.get_all(
            "Sales Order Item",
            filters={"parent": ["in", names], "prevdoc_docname": ["is", "set"]},
            pluck="parent",
        )
    )
    for o in orders:
        if o.name not in with_team:
            add(
                _("Sales Order has no Sales Team"),
                "Sales Order",
                o.name,
                o.transaction_date,
                _("No Sales Engineer is credited for this order."),
            )
        if o.name not in from_quote:
            add(
                _("Sales Order not made from a quotation"),
                "Sales Order",
                o.name,
                o.transaction_date,
                _("Hit rate and sales cycle cannot follow it back to the first contact."),
                "Medium",
            )
        if o.po_no and not o.po_date:
            add(
                _("Customer PO has no date"),
                "Sales Order",
                o.name,
                o.transaction_date,
                _("The 48-hour record check cannot be measured."),
                "Low",
            )

    # Sales persons and employees
    for sp in frappe.get_all(
        "Sales Person", filters={"enabled": 1, "is_group": 0, "employee": ["is", "not set"]}, pluck="name"
    ):
        add(
            _("Sales Person not linked to an Employee"),
            "Sales Person",
            sp,
            None,
            _("Orders credited to this sales person do not reach any scorecard."),
        )
    for emp in frappe.get_all(
        "Employee",
        filters={"status": "Active", "kpi_template": ["is", "set"], **company},
        fields=["name", "user_id", "kpi_template"],
    ):
        if not emp.user_id:
            add(
                _("Employee has a KPI Template but no User"),
                "Employee",
                emp.name,
                None,
                _("Their quotations cannot be assigned automatically and they cannot see their scorecard."),
                "Medium",
            )
        role = frappe.db.get_value("KPI Template", emp.kpi_template, "kpi_role")
        if role == "Sales Engineer" and not frappe.db.exists("Sales Person", {"employee": emp.name}):
            add(
                _("Sales Engineer has no Sales Person"),
                "Employee",
                emp.name,
                None,
                _("Sales, hit rate and repeat revenue will be empty."),
            )

    # Stale deals
    stale_deals = add_days(nowdate(), -cint(settings.stale_deal_days or 14))
    for opp in frappe.get_all(
        "Opportunity",
        filters={
            "status": ["in", ["Open", "Replied", "Quotation"]],
            "modified": ["<", stale_deals],
            **company,
        },
        fields=["name", "modified", "opportunity_owner"],
        limit_page_length=0,
    ):
        add(
            _("Open opportunity not updated for {0} days").format(settings.stale_deal_days),
            "Opportunity",
            opp.name,
            opp.modified,
            opp.opportunity_owner,
            "Low",
        )
    if frappe.db.exists("DocType", "CRM Deal"):
        for deal in frappe.get_all(
            "CRM Deal",
            filters={"status": ["not in", ["Won", "Lost"]], "modified": ["<", stale_deals]},
            fields=["name", "modified", "deal_owner"],
            limit_page_length=0,
        ):
            add(
                _("Open CRM deal not updated for {0} days").format(settings.stale_deal_days),
                "CRM Deal",
                deal.name,
                deal.modified,
                deal.deal_owner,
                "Low",
            )

    # Deal updates recorded without the real change date
    for log in frappe.get_all(
        "KPI Deal Update Log",
        filters={"event_date_given": 0, "logged_on": ["between", [start, end]]},
        fields=["name", "logged_on", "reference_name"],
        limit_page_length=0,
    ):
        add(
            _("Deal change recorded without its real date"),
            "KPI Deal Update Log",
            log.name,
            log.logged_on,
            log.reference_name,
            "Low",
        )

    # Technical queries never answered
    for q in frappe.get_all(
        "Technical Query",
        filters={"status": "Open", "received_on": ["<", get_datetime(add_days(nowdate(), -2))]},
        fields=["name", "received_on", "employee_name"],
    ):
        add(
            _("Technical query still open"),
            "Technical Query",
            q.name,
            q.received_on,
            q.employee_name,
            "Medium",
        )

    order = {"High": 0, "Medium": 1, "Low": 2}
    data.sort(key=lambda d: (order[d["severity"]], d["issue"]))
    summary = [
        {
            "label": _(level),
            "value": sum(1 for d in data if d["severity"] == level),
            "datatype": "Int",
            "indicator": colour,
        }
        for level, colour in (("High", "Red"), ("Medium", "Orange"), ("Low", "Blue"))
    ]
    return columns(), data, None, None, summary


def columns():
    return [
        {"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
        {"label": _("Issue"), "fieldname": "issue", "fieldtype": "Data", "width": 300},
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
            "width": 170,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Data", "width": 150},
        {"label": _("Details"), "fieldname": "details", "fieldtype": "Data", "width": 320},
    ]
