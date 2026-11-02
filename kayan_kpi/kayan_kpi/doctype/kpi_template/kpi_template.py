# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class KPITemplate(Document):
    def validate(self):
        self.total_weight = round(sum(flt(r.weight) for r in self.items), 2)
        if self.is_active and abs(self.total_weight - 100) > 0.001:
            frappe.throw(
                _("KPI weights add up to {0}%. An active template must total 100%.").format(
                    self.total_weight
                ),
                title=_("Weights"),
            )
        for row in self.items:
            if flt(row.target_value) < 0:
                frappe.throw(_("Row {0}: the target cannot be negative.").format(row.idx))
