import frappe
from frappe import _
from frappe.utils import now_datetime

from kayan_kpi.patches.v1_0.backfill_quotation_kpi_fields import backfill


@frappe.whitelist()
def recalculate_scorecard(name: str):
    doc = frappe.get_doc("KPI Scorecard", name)
    doc.check_permission("write")
    if doc.docstatus != 0:
        frappe.throw(_("Only draft scorecards can be recalculated."))
    doc.calculate()
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def create_scorecards(period: str):
    """One scorecard per active employee with a KPI Template, for the period."""
    frappe.only_for(("KPI Manager", "System Manager"))
    kpi_period = frappe.get_doc("KPI Period", period)
    if kpi_period.status != "Open":
        frappe.throw(_("{0} is closed.").format(period))
    filters = {"status": "Active", "kpi_template": ["is", "set"]}
    if kpi_period.company:
        filters["company"] = kpi_period.company
    created, existing = [], []
    for emp in frappe.get_all("Employee", filters=filters, fields=["name", "kpi_template"]):
        if not frappe.db.get_value("KPI Template", emp.kpi_template, "is_active"):
            continue
        if frappe.db.exists(
            "KPI Scorecard", {"employee": emp.name, "kpi_period": period, "docstatus": ["<", 2]}
        ):
            existing.append(emp.name)
            continue
        doc = frappe.get_doc(
            {
                "doctype": "KPI Scorecard",
                "employee": emp.name,
                "kpi_period": period,
                "kpi_template": emp.kpi_template,
            }
        )
        doc.calculate()
        doc.insert()
        created.append(doc.name)
    return {"created": created, "existing": existing}


@frappe.whitelist()
def mark_query_replied(name: str):
    doc = frappe.get_doc("Technical Query", name)
    doc.check_permission("write")
    if not doc.first_reply_on:
        doc.first_reply_on = now_datetime()
        doc.save()
    return doc.as_dict()


@frappe.whitelist()
def backfill_quotations():
    """Fill KPI fields on quotations submitted before Kayan KPI was installed."""
    frappe.only_for(("KPI Manager", "System Manager"))
    frappe.enqueue(backfill, queue="long", timeout=3000, job_id="kayan_kpi_backfill", deduplicate=True)
    return _("Backfill started. Quotations will be updated in the background.")
