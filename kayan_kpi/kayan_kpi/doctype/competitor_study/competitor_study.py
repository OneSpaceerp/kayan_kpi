# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from kayan_kpi.kpi.common import get_employee_for_user, get_employee_role, get_settings
from kayan_kpi.kpi.metrics.shared import study_score


class CompetitorStudy(Document):
    def before_validate(self):
        if not self.employee:
            self.employee = get_employee_for_user(frappe.session.user)
        if self.employee and not self.kpi_role:
            self.kpi_role = get_employee_role(self.employee)

    def validate(self):
        ready_on = frappe.db.get_value("Quotation", self.quotation, "kpi_ready_on")
        if self.is_new():
            self.creation = self.creation or now_datetime()
        self.study_score, on_time = study_score(self, ready_on, get_settings().competitor_checklist_weight)
        self.submitted_on_time = 1 if on_time else 0

    def before_submit(self):
        if "KPI Manager" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
            frappe.throw(_("A KPI Manager completes the review and submits the study."))
