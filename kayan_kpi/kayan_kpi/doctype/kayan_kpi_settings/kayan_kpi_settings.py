# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class KayanKPISettings(Document):
    def validate(self):
        if cint(self.allow_over_achievement) and flt(self.max_achievement_percent) < 100:
            frappe.throw(_("Maximum Achievement % must be 100 or more."))
        if cint(self.sla_working_days) < 1:
            frappe.throw(_("The quotation SLA must be at least 1 working day."))
        if not 0 <= flt(self.competitor_checklist_weight) <= 100:
            frappe.throw(_("Checklist Weight % must be between 0 and 100."))
        if self.crm_source == "Frappe CRM" and not frappe.db.exists("DocType", "CRM Deal"):
            frappe.msgprint(
                _(
                    "Frappe CRM is not installed on this site. Quotations will use the CRM Deal entered on the "
                    "quotation and their own request time."
                ),
                indicator="orange",
            )

    def on_update(self):
        frappe.cache.delete_keys("kayan_kpi_holidays::")
