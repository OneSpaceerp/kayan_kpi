"""Lookups shared by the metrics, the document events and the reports."""

from collections import defaultdict
from dataclasses import dataclass, field

import frappe
from frappe.utils import add_days, add_months, cint, flt, get_datetime, getdate

APPLICATION = "Application Engineer"
SALES = "Sales Engineer"
WON_STATUSES = ("Ordered", "Partially Ordered")


def get_settings():
    return frappe.get_cached_doc("Kayan KPI Settings")


@dataclass
class MetricContext:
    employee: str
    role: str
    start: object  # date
    end: object  # date
    settings: object
    company: str | None = None
    period: str | None = None
    target: float = 0.0
    _cache: dict = field(default_factory=dict)

    @property
    def start_dt(self):
        return get_datetime(f"{self.start} 00:00:00")

    @property
    def end_dt(self):
        return get_datetime(f"{self.end} 23:59:59.999999")


@dataclass
class MetricResult:
    actual: float | None
    numerator: float = 0.0
    denominator: float = 0.0
    details: str = ""
    rows: list = field(default_factory=list)


def evidence(doctype, name, date=None, party=None, credit=1.0, value=None, result=None, note=None):
    return {
        "doctype": doctype,
        "name": name,
        "date": date,
        "party": party,
        "credit": round(flt(credit), 4),
        "value": value,
        "result": result,
        "note": note,
    }


# --- holidays ---------------------------------------------------------------


def get_holiday_list(company=None):
    settings = get_settings()
    if settings.holiday_list:
        return settings.holiday_list
    company = company or settings.company or frappe.defaults.get_global_default("company")
    if company:
        return frappe.get_cached_value("Company", company, "default_holiday_list")
    return None


def get_holidays(company=None):
    """Set of holiday dates (weekends included) from the configured Holiday List."""
    holiday_list = get_holiday_list(company)
    if not holiday_list:
        return set()
    key = f"kayan_kpi_holidays::{holiday_list}"
    cached = frappe.cache.get_value(key)
    if cached is None:
        cached = [
            str(d) for d in frappe.get_all("Holiday", filters={"parent": holiday_list}, pluck="holiday_date")
        ]
        frappe.cache.set_value(key, cached, expires_in_sec=3600)
    return {getdate(d) for d in cached}


# --- people -----------------------------------------------------------------


def get_employee_for_user(user):
    if not user or user in ("Guest", "Administrator"):
        return None
    return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def get_user_for_employee(employee):
    return frappe.db.get_value("Employee", employee, "user_id") if employee else None


def get_sales_persons(employee):
    return frappe.get_all("Sales Person", filters={"employee": employee}, pluck="name")


def get_employee_role(employee):
    template = frappe.db.get_value("Employee", employee, "kpi_template")
    return frappe.db.get_value("KPI Template", template, "kpi_role") if template else None


# --- credit rules -----------------------------------------------------------


def _credit_from_rows(rows, employee, rule):
    """Credit for `employee` among the engineer rows of one role on one document."""
    mine = [r for r in rows if r.employee == employee]
    if not mine:
        return 0.0
    if rule == "Full Credit to Each":
        return 1.0
    if rule == "Split Equally":
        return 1.0 / len(rows)
    primary = [r for r in rows if cint(r.is_primary)] or sorted(rows, key=lambda r: r.idx)[:1]
    return 1.0 if any(r.employee == employee for r in primary) else 0.0


def quotation_credits(ctx, quotation_names):
    """{quotation: credit} for the context employee, using the role on the scorecard."""
    if not quotation_names:
        return {}
    rows = frappe.get_all(
        "KPI Quotation Engineer",
        filters={"parenttype": "Quotation", "parent": ["in", list(quotation_names)], "kpi_role": ctx.role},
        fields=["parent", "employee", "is_primary", "idx"],
    )
    by_parent = defaultdict(list)
    for row in rows:
        by_parent[row.parent].append(row)
    rule = ctx.settings.quotation_credit_rule
    credits = {}
    for parent, parent_rows in by_parent.items():
        credit = _credit_from_rows(parent_rows, ctx.employee, rule)
        if credit:
            credits[parent] = credit
    return credits


def employee_quotations(ctx, filters, fields=None):
    """Quotations matching `filters` where the context employee is one of the engineers of the role.

    Returns (list of quotation rows, {name: credit}).
    """
    QE = frappe.qb.DocType("KPI Quotation Engineer")
    names = (
        frappe.qb.from_(QE)
        .select(QE.parent)
        .distinct()
        .where((QE.parenttype == "Quotation") & (QE.employee == ctx.employee) & (QE.kpi_role == ctx.role))
    ).run(pluck=True)
    if not names:
        return [], {}
    filters = dict(filters)
    if "name" in filters:
        # the caller already narrowed the quotations (e.g. to reviewed ones): keep both conditions
        names = sorted(set(names) & set(filters["name"][1]))
        if not names:
            return [], {}
    filters["name"] = ["in", names]
    quotations = frappe.get_all("Quotation", filters=filters, fields=fields or ["name"], limit_page_length=0)
    credits = quotation_credits(ctx, [q.name for q in quotations])
    quotations = [q for q in quotations if credits.get(q.name)]
    return quotations, credits


def sales_team_credits(ctx, doctype, names):
    """{document: credit} for the context employee from the Sales Team allocation."""
    sales_persons = ctx._cache.get("sales_persons")
    if sales_persons is None:
        sales_persons = ctx._cache["sales_persons"] = set(get_sales_persons(ctx.employee))
    if not names or not sales_persons:
        return {}
    rows = frappe.get_all(
        "Sales Team",
        filters={"parenttype": doctype, "parent": ["in", list(names)]},
        fields=["parent", "sales_person", "allocated_percentage", "idx"],
    )
    by_parent = defaultdict(list)
    for row in rows:
        by_parent[row.parent].append(row)
    rule = ctx.settings.quotation_credit_rule
    credits = {}
    for parent, team in by_parent.items():
        mine = [r for r in team if r.sales_person in sales_persons]
        if not mine:
            continue
        if rule == "Full Credit to Each":
            credit = 1.0
        elif rule == "Split Equally":
            total = sum(flt(r.allocated_percentage) for r in team)
            credit = (
                sum(flt(r.allocated_percentage) for r in mine) / total if total else len(mine) / len(team)
            )
        else:
            lead = sorted(team, key=lambda r: (-flt(r.allocated_percentage), r.idx))[0]
            credit = 1.0 if lead.sales_person in sales_persons else 0.0
        if credit:
            credits[parent] = credit
    return credits


def employee_sales_documents(ctx, doctype, filters, fields):
    """Submitted Sales Orders / Sales Invoices credited to the context employee."""
    sales_persons = get_sales_persons(ctx.employee)
    ctx._cache["sales_persons"] = set(sales_persons)
    if not sales_persons:
        return [], {}
    names = frappe.get_all(
        "Sales Team",
        filters={"parenttype": doctype, "sales_person": ["in", sales_persons]},
        pluck="parent",
        distinct=True,
        limit_page_length=0,
    )
    if not names:
        return [], {}
    filters = dict(filters)
    filters["name"] = ["in", names]
    filters["docstatus"] = 1
    docs = frappe.get_all(doctype, filters=filters, fields=fields, limit_page_length=0)
    credits = sales_team_credits(ctx, doctype, [d.name for d in docs])
    return [d for d in docs if credits.get(d.name)], credits


def sales_date_field(doctype):
    return "posting_date" if doctype == "Sales Invoice" else "transaction_date"


def customer_had_orders_before(doctype, customers, before, lookback_months=0):
    """Customers that have a submitted document of `doctype` dated before `before`."""
    if not customers:
        return set()
    date_field = sales_date_field(doctype)
    filters = {"docstatus": 1, "customer": ["in", list(customers)], date_field: ["<", before]}
    if cint(lookback_months):
        filters[date_field] = [
            "between",
            [add_months(before, -cint(lookback_months)), add_days(before, -1)],
        ]
    if doctype == "Sales Invoice":
        filters["is_return"] = 0
    return set(frappe.get_all(doctype, filters=filters, pluck="customer", distinct=True, limit_page_length=0))
