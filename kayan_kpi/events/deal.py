"""Opportunity and CRM Deal: log every stage or status change for the 48-hour record KPI."""

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime

from kayan_kpi.kpi.common import get_employee_for_user, get_settings
from kayan_kpi.kpi.working_days import hours_between

TRACKED = {
    "Opportunity": (("sales_stage", "Stage Change"), ("status", "Status Change")),
    "CRM Deal": (("status", "Status Change"),),
}
OWNER_FIELD = {"Opportunity": "opportunity_owner", "CRM Deal": "deal_owner"}


# ERPNext moves an Opportunity to Quotation / Converted / Replied by itself; only
# the decisions a person makes are measured.
USER_STATUSES = {"Opportunity": ("Lost", "Closed", "Open")}


def _changes(doc):
    before = doc.get_doc_before_save()
    if not before:
        return []
    changes = []
    for field, label in TRACKED.get(doc.doctype, ()):
        old, new = before.get(field), doc.get(field)
        if old == new:
            continue
        if field == "status" and doc.doctype in USER_STATUSES and new not in USER_STATUSES[doc.doctype]:
            continue
        changes.append((label, old, new))
    return changes


def validate(doc, method=None):
    if doc.doctype != "Opportunity" or doc.is_new():
        return
    if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_migrate:
        return
    if not cint(get_settings().require_event_date_on_stage_change):
        return
    stage_changed = any(label == "Stage Change" for label, _old, _new in _changes(doc))
    if stage_changed and not doc.get("kpi_event_on"):
        frappe.throw(
            _("Enter when this change actually happened in KPI Tracking → Change Happened On."),
            title=_("Change Date Required"),
        )
    if doc.get("kpi_event_on") and get_datetime(doc.kpi_event_on) > now_datetime():
        frappe.throw(_("Change Happened On cannot be in the future."))


def on_update(doc, method=None):
    changes = _changes(doc)
    if not changes:
        return
    employee = doc.get("kpi_sales_engineer") or get_employee_for_user(doc.get(OWNER_FIELD[doc.doctype]))
    if not employee:
        return

    logged_on = now_datetime()
    given = bool(doc.get("kpi_event_on"))
    event_on = get_datetime(doc.kpi_event_on) if given else logged_on
    lag = max(hours_between(event_on, logged_on) or 0, 0)
    target = flt(get_settings().record_update_hours) or 48
    for update_type, old, new in changes:
        frappe.get_doc(
            {
                "doctype": "KPI Deal Update Log",
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "employee": employee,
                "update_type": update_type,
                "from_value": str(old or ""),
                "to_value": str(new or ""),
                "event_on": event_on,
                "logged_on": logged_on,
                "event_date_given": 1 if given else 0,
                "lag_hours": lag,
                "within_target": 1 if lag <= target else 0,
            }
        ).insert(ignore_permissions=True)

    # the next change needs its own date
    if given and doc.meta.has_field("kpi_event_on"):
        doc.db_set("kpi_event_on", None, update_modified=False)
