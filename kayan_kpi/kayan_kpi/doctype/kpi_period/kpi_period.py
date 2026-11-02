# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class KPIPeriod(Document):
    def validate(self):
        if getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End Date cannot be before Start Date."))
        seen = set()
        for row in self.sales_targets:
            if row.employee in seen:
                frappe.throw(_("Row {0}: {1} has more than one sales target.").format(row.idx, row.employee))
            seen.add(row.employee)
