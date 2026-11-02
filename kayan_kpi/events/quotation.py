"""Quotation: who gets credit, when the clock started, and when the quotation was ready."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from kayan_kpi.kpi.common import APPLICATION, SALES, get_employee_for_user, get_employee_role, get_settings
from kayan_kpi.kpi.metrics.application import required_document_types
from kayan_kpi.kpi.sources import apply_request_info, apply_sla


def validate(doc, method=None):
    info = apply_request_info(doc)
    _add_engineers(doc, info)
    _mark_primary(doc)
    apply_sla(doc)


def before_submit(doc, method=None):
    settings = get_settings()
    if cint(settings.require_engineer_on_quotation) and not doc.get("kpi_engineers"):
        frappe.throw(
            _("Add the Application or Sales Engineer in the KPI tab before submitting."),
            title=_("Engineer Required"),
        )
    if cint(settings.block_submit_without_documents):
        attached = {d.document_type for d in doc.get("kpi_documents") or [] if d.attachment}
        missing = [d for d in required_document_types(settings) if d not in attached]
        if missing:
            frappe.throw(
                _("Attach the {0} in the KPI tab before submitting.").format(
                    ", ".join(_(m).lower() for m in missing)
                ),
                title=_("Documents Required"),
            )
    if not doc.get("kpi_request_received_on"):
        doc.kpi_request_received_on = doc.creation or now_datetime()
        doc.kpi_request_source = _("Quotation created (no request recorded)")
        if not doc.get("kpi_first_contact_on"):
            doc.kpi_first_contact_on = doc.kpi_request_received_on
    apply_sla(doc, ready_on=now_datetime())


def on_cancel(doc, method=None):
    # a cancelled quotation is not counted; an amendment gets its own ready time on submit
    pass


def _add_engineers(doc, info):
    existing = {(r.employee, r.kpi_role) for r in doc.get("kpi_engineers") or []}

    def add(employee, role):
        if employee and (employee, role) not in existing:
            doc.append("kpi_engineers", {"employee": employee, "kpi_role": role})
            existing.add((employee, role))

    add(info.get("application_engineer"), APPLICATION)
    add(info.get("sales_engineer"), SALES)

    if doc.get("kpi_engineers") or not cint(get_settings().auto_assign_quotation_engineer):
        return
    employee = get_employee_for_user(doc.owner or frappe.session.user)
    role = get_employee_role(employee) if employee else None
    if role in (APPLICATION, SALES):
        add(employee, role)


def _mark_primary(doc):
    for role in (APPLICATION, SALES):
        rows = [r for r in doc.get("kpi_engineers") or [] if r.kpi_role == role]
        primaries = [r for r in rows if cint(r.is_primary)]
        if rows and not primaries:
            rows[0].is_primary = 1
        elif len(primaries) > 1:
            frappe.throw(_("Only one primary {0} is allowed on a quotation.").format(_(role)))
