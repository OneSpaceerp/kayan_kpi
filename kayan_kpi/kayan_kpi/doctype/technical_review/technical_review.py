# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kayan_kpi.kpi.common import APPLICATION


class TechnicalReview(Document):
    def validate(self):
        if frappe.db.get_value("Quotation", self.quotation, "docstatus") != 1:
            frappe.throw(_("Only submitted quotations can be reviewed."))
        if not self.application_engineer:
            self.application_engineer = frappe.db.get_value(
                "KPI Quotation Engineer",
                {
                    "parenttype": "Quotation",
                    "parent": self.quotation,
                    "kpi_role": APPLICATION,
                    "is_primary": 1,
                },
                "employee",
            )

    def on_submit(self):
        # close the random-sample assignment, if there was one
        for todo in frappe.get_all(
            "ToDo",
            filters={"reference_type": "Quotation", "reference_name": self.quotation, "status": "Open"},
            pluck="name",
        ):
            frappe.db.set_value("ToDo", todo, "status", "Closed")
