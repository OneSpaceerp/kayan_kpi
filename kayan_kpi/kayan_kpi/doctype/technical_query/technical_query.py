# Copyright (c) 2026, Nest Software Development and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime

from kayan_kpi.kpi.common import get_employee_for_user, get_settings
from kayan_kpi.kpi.working_days import hours_between


class TechnicalQuery(Document):
    def before_validate(self):
        if not self.employee:
            self.employee = get_employee_for_user(frappe.session.user)

    def validate(self):
        if self.first_reply_on and get_datetime(self.first_reply_on) < get_datetime(self.received_on):
            frappe.throw(_("First Reply On cannot be before Received On."))
        if self.first_reply_on:
            self.reply_hours = hours_between(
                get_datetime(self.received_on), get_datetime(self.first_reply_on)
            )
            self.replied_on_time = (
                1 if self.reply_hours <= (flt(get_settings().query_reply_hours) or 24) else 0
            )
            if self.status == "Open":
                self.status = "Replied"
        else:
            self.reply_hours = 0
            self.replied_on_time = 0
