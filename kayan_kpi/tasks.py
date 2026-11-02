"""Scheduled jobs."""

import math
import random

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign
from frappe.utils import add_days, cint, flt, get_datetime, now_datetime

from kayan_kpi.kpi.common import get_settings

SAMPLE_NOTE = "Kayan KPI: random technical review"


def recalculate_open_scorecards():
    if not cint(get_settings().recalculate_daily):
        return
    open_periods = frappe.get_all("KPI Period", filters={"status": "Open"}, pluck="name")
    if not open_periods:
        return
    for name in frappe.get_all(
        "KPI Scorecard", filters={"docstatus": 0, "kpi_period": ["in", open_periods]}, pluck="name"
    ):
        try:
            doc = frappe.get_doc("KPI Scorecard", name)
            doc.calculate()
            doc.flags.ignore_permissions = True
            doc.save()
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=_("Kayan KPI: could not recalculate {0}").format(name))


def assign_random_reviews():
    """Assign a random sample of last week's quotations to the KPI Managers for a technical review."""
    percent = flt(get_settings().review_sample_percent)
    if percent <= 0:
        return
    managers = [
        u
        for u in frappe.get_all(
            "Has Role", filters={"role": "KPI Manager", "parenttype": "User"}, pluck="parent", distinct=True
        )
        if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
    ]
    if not managers:
        return
    since = get_datetime(add_days(now_datetime(), -7))
    reviewed = set(frappe.get_all("Technical Review", filters={"docstatus": ["<", 2]}, pluck="quotation"))
    candidates = [
        q
        for q in frappe.get_all(
            "Quotation", filters={"docstatus": 1, "kpi_ready_on": [">=", since]}, pluck="name"
        )
        if q not in reviewed
    ]
    if not candidates:
        return
    sample = random.sample(candidates, min(len(candidates), math.ceil(len(candidates) * percent / 100)))
    for i, quotation in enumerate(sample):
        if frappe.db.exists(
            "ToDo", {"reference_type": "Quotation", "reference_name": quotation, "description": SAMPLE_NOTE}
        ):
            continue
        assign(
            {
                "assign_to": [managers[i % len(managers)]],
                "doctype": "Quotation",
                "name": quotation,
                "description": SAMPLE_NOTE,
                "notify": 1,
            },
            ignore_permissions=True,
        )
