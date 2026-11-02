"""Engineers see their own KPI records; managers also see everyone who reports to them.

KPI Manager and System Manager see everything. "Reports to" is the Employee tree, so
a manager sees the whole team under them, not only direct reports.
"""

import frappe

FULL_ACCESS = ("KPI Manager", "System Manager")
EMPLOYEE_FIELD = {
    "KPI Scorecard": "employee",
    "Technical Query": "employee",
    "Competitor Study": "employee",
    "KPI Deal Update Log": "employee",
}


def visible_employees(user):
    """Employees whose KPI records `user` may see, or None for everyone."""
    if user == "Administrator" or set(FULL_ACCESS) & set(frappe.get_roles(user)):
        return None
    key = f"kayan_kpi_visible::{user}"
    cached = frappe.cache.get_value(key)
    if cached is not None:
        return cached
    visible = set()
    for me in frappe.get_all("Employee", filters={"user_id": user}, fields=["name", "lft", "rgt"]):
        visible.add(me.name)
        if me.lft and me.rgt:
            visible.update(
                frappe.get_all("Employee", filters={"lft": [">", me.lft], "rgt": ["<", me.rgt]}, pluck="name")
            )
    visible = sorted(visible)
    frappe.cache.set_value(key, visible, expires_in_sec=300)
    return visible


def _condition(doctype, user):
    user = user or frappe.session.user
    visible = visible_employees(user)
    if visible is None:
        return ""
    if not visible:
        return "1=0"
    values = ", ".join(frappe.db.escape(e) for e in visible)
    field = EMPLOYEE_FIELD[doctype]
    return f"`tab{doctype}`.`{field}` in ({values})"


def _has_permission(doc, user):
    visible = visible_employees(user or frappe.session.user)
    if visible is None:
        return True
    employee = doc.get(EMPLOYEE_FIELD[doc.doctype])
    # new documents are checked by role permissions only
    return not employee or employee in visible


def scorecard_query(user=None, doctype=None):
    return _condition("KPI Scorecard", user)


def technical_query_query(user=None, doctype=None):
    return _condition("Technical Query", user)


def competitor_study_query(user=None, doctype=None):
    return _condition("Competitor Study", user)


def deal_log_query(user=None, doctype=None):
    return _condition("KPI Deal Update Log", user)


def has_permission(doc, ptype=None, user=None, debug=False):
    return _has_permission(doc, user)
