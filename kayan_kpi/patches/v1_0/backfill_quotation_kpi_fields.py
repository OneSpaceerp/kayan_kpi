"""Fill KPI fields on quotations submitted before Kayan KPI was installed (for the Q3 backfill).

Safe to run again: only empty fields are filled. The ready time is the first time the
quotation was saved as submitted in its version history, else its last change.
"""

import frappe
from frappe.utils import get_datetime

from kayan_kpi.events.quotation import _add_engineers, _mark_primary
from kayan_kpi.kpi.sources import apply_request_info, apply_sla


def _submitted_on(name):
    versions = frappe.get_all(
        "Version",
        filters={"ref_doctype": "Quotation", "docname": name, "data": ["like", '%"docstatus"%']},
        fields=["creation"],
        order_by="creation asc",
        limit=1,
    )
    return versions[0].creation if versions else None


def backfill():
    """Quotations without a ready time get their KPI fields and engineers filled."""
    names = frappe.get_all(
        "Quotation",
        filters={"docstatus": 1, "kpi_ready_on": ["is", "not set"]},
        pluck="name",
        limit_page_length=0,
    )
    for name in names:
        doc = frappe.get_doc("Quotation", name)
        info = apply_request_info(doc)
        _add_engineers(doc, info)
        _mark_primary(doc)
        for row in doc.get("kpi_engineers") or []:
            if not frappe.db.exists("KPI Quotation Engineer", row.name or ""):
                row.db_insert()
        if not doc.get("kpi_request_received_on"):
            doc.kpi_request_received_on = doc.creation
            doc.kpi_request_source = "Quotation created (no request recorded)"
        if not doc.get("kpi_first_contact_on"):
            doc.kpi_first_contact_on = doc.kpi_request_received_on
        ready = _submitted_on(name) or doc.modified
        apply_sla(doc, ready_on=get_datetime(ready))
        values = {
            f: doc.get(f)
            for f in (
                "kpi_crm_deal",
                "kpi_request_received_on",
                "kpi_request_source",
                "kpi_inquiry_complexity",
                "kpi_agreed_due_on",
                "kpi_first_contact_on",
                "kpi_due_on",
                "kpi_ready_on",
                "kpi_tat_hours",
                "kpi_within_sla",
            )
        }
        frappe.db.set_value("Quotation", name, values, update_modified=False)
    frappe.db.commit()


def execute():
    backfill()
