# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from kayan_kpi.kpi import engine
from kayan_kpi.kpi.common import get_settings, get_user_for_employee


class KPIScorecard(Document):
    def validate(self):
        self.validate_duplicate()
        if not self.reviewer:
            reports_to = frappe.db.get_value("Employee", self.employee, "reports_to")
            self.reviewer = get_user_for_employee(reports_to)
        for row in self.items:
            if cint(row.override) and not (row.override_reason or "").strip():
                frappe.throw(_("Row {0}: give a reason for the entered actual.").format(row.idx))
            if cint(row.override) and row.data_source == "Automatic":
                row.data_source = "Manual"
            if not cint(row.override) and row.metric != "Manual Entry":
                row.data_source = "Automatic"
        if not self.items:
            engine.calculate(self)
        else:
            engine.apply_scoring(self)

    def validate_duplicate(self):
        existing = frappe.db.exists(
            "KPI Scorecard",
            {
                "employee": self.employee,
                "kpi_period": self.kpi_period,
                "docstatus": ["<", 2],
                "name": ["!=", self.name],
            },
        )
        if existing and not self.amended_from:
            frappe.throw(
                _("{0} already has scorecard {1} for {2}.").format(
                    self.employee_name or self.employee, existing, self.kpi_period
                ),
                title=_("Duplicate Scorecard"),
            )

    def calculate(self):
        engine.calculate(self)

    def before_submit(self):
        if not self.last_calculated_on:
            frappe.throw(_("Calculate the scorecard before approving it."))
        self.status = "Approved"

    def on_submit(self):
        if cint(get_settings().sync_hrms_goals):
            sync_goals(self)

    def on_cancel(self):
        self.db_set("status", "Cancelled")


def sync_goals(scorecard):
    """Each KPI with a KRA becomes an HRMS Goal in the period's Appraisal Cycle."""
    if not frappe.db.exists("DocType", "Goal"):
        return
    period = frappe.get_cached_doc("KPI Period", scorecard.kpi_period)
    if not period.appraisal_cycle:
        frappe.msgprint(_("Set an Appraisal Cycle on {0} to sync goals to HRMS.").format(period.name))
        return
    synced = 0
    for row in scorecard.items:
        if not row.kra:
            continue
        goal_name = f"{row.goal} ({scorecard.kpi_period})"
        name = frappe.db.get_value(
            "Goal",
            {
                "employee": scorecard.employee,
                "appraisal_cycle": period.appraisal_cycle,
                "goal_name": goal_name,
            },
        )
        goal = frappe.get_doc("Goal", name) if name else frappe.new_doc("Goal")
        goal.update(
            {
                "goal_name": goal_name,
                "employee": scorecard.employee,
                "appraisal_cycle": period.appraisal_cycle,
                "kra": row.kra,
                "start_date": getdate(period.start_date),
                "end_date": getdate(period.end_date),
                "progress": min(flt(row.achievement_percent), 100),
                "description": _("Kayan KPI {0}: {1}").format(scorecard.name, row.details or ""),
            }
        )
        try:
            goal.flags.ignore_permissions = True
            goal.save()
            synced += 1
        except frappe.ValidationError as e:
            frappe.msgprint(_("Goal '{0}' was not synced: {1}").format(goal_name, e), indicator="orange")
    if synced:
        frappe.msgprint(_("{0} goals synced to HRMS.").format(synced), indicator="green", alert=True)
