"""Sales Engineer KPIs (Goals for Sales Engineers, Q3-Q4)."""

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_datetime, getdate

from kayan_kpi.kpi.common import (
    MetricResult,
    customer_had_orders_before,
    employee_quotations,
    employee_sales_documents,
    evidence,
    sales_date_field,
)
from kayan_kpi.kpi.scoring import ratio
from kayan_kpi.kpi.sources import in_hand_dates, po_event_time
from kayan_kpi.kpi.working_days import month_overlap_fraction

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip


def _basis(ctx):
    return ctx.settings.sales_basis or "Sales Order"


def _sales_docs(ctx, start=None, end=None, extra_fields=()):
    doctype = _basis(ctx)
    date_field = sales_date_field(doctype)
    fields = ["name", "customer", "customer_name", date_field, "base_net_total", *extra_fields]
    docs, credits = employee_sales_documents(
        ctx, doctype, {date_field: ["between", [start or ctx.start, end or ctx.end]]}, fields
    )
    for d in docs:
        d.doc_date = d.get(date_field)
    return doctype, docs, credits


# --- sales target -----------------------------------------------------------


def _sales_person_target(ctx):
    from kayan_kpi.kpi.common import get_sales_persons

    sales_persons = get_sales_persons(ctx.employee)
    if not sales_persons:
        return 0.0, _("Employee is not linked to a Sales Person")
    rows = frappe.get_all(
        "Target Detail",
        filters={"parenttype": "Sales Person", "parent": ["in", sales_persons]},
        fields=["fiscal_year", "target_amount", "distribution_id"],
        limit_page_length=0,
    )
    start, end = getdate(ctx.start), getdate(ctx.end)
    total = 0.0
    for row in rows:
        fy = frappe.get_cached_value("Fiscal Year", row.fiscal_year, ["year_start_date", "year_end_date"])
        if not fy:
            continue
        fy_start, fy_end = getdate(fy[0]), getdate(fy[1])
        lo, hi = max(start, fy_start), min(end, fy_end)
        if hi < lo:
            continue
        percentages = {}
        if row.distribution_id:
            for p in frappe.get_all(
                "Monthly Distribution Percentage",
                filters={"parent": row.distribution_id},
                fields=["month", "percentage_allocation"],
            ):
                percentages[p.month] = flt(p.percentage_allocation)
        y, m = lo.year, lo.month
        while date(y, m, 1) <= hi:
            share = percentages.get(MONTHS[m - 1], 100.0 / 12) if percentages else 100.0 / 12
            total += flt(row.target_amount) * share / 100.0 * month_overlap_fraction(y, m, lo, hi)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return round(total, 2), _("Sales Person targets")


def _period_target(ctx):
    if not ctx.period:
        return 0.0, _("No KPI Period")
    amount = frappe.db.get_value(
        "KPI Period Sales Target", {"parent": ctx.period, "employee": ctx.employee}, "target_amount"
    )
    return flt(amount), _("KPI Period targets")


def sales_target_achievement(ctx):
    if ctx.settings.sales_target_source == "KPI Period Targets":
        target, source = _period_target(ctx)
    else:
        target, source = _sales_person_target(ctx)
    doctype, docs, credits = _sales_docs(ctx)
    achieved = 0.0
    rows = []
    for d in docs:
        amount = flt(d.base_net_total) * credits[d.name]
        achieved += amount
        rows.append(evidence(doctype, d.name, d.doc_date, d.customer_name, credits[d.name], round(amount, 2)))
    if not target:
        return MetricResult(None, achieved, 0, _("No sales target for the period ({0})").format(source), rows)
    return MetricResult(
        ratio(achieved, target),
        round(achieved, 2),
        target,
        _("{0} sold of a {1} target ({2}, {3})").format(
            frappe.format(achieved, "Currency"), frappe.format(target, "Currency"), _(doctype), source
        ),
        rows,
    )


# --- hit rate ---------------------------------------------------------------


def quotation_hit_rate(ctx):
    """Paid orders in hand in the period / quotations issued in the period (both credited to the engineer)."""
    quotations, q_credits = employee_quotations(
        ctx, {"docstatus": 1, "transaction_date": ["between", [ctx.start, ctx.end]]}, ["name"]
    )
    issued = sum(q_credits[q.name] for q in quotations)
    orders, o_credits = employee_sales_documents(
        ctx,
        "Sales Order",
        {"transaction_date": ["between", [add_days(ctx.start, -365), ctx.end]]},
        ["name", "customer_name", "transaction_date", "po_no", "po_date", "advance_paid", "grand_total"],
    )
    dates = in_hand_dates(orders, ctx.settings)
    in_hand = 0.0
    rows = []
    for o in orders:
        when = dates.get(o.name)
        if when and getdate(ctx.start) <= when <= getdate(ctx.end):
            in_hand += o_credits[o.name]
            rows.append(
                evidence(
                    "Sales Order",
                    o.name,
                    when,
                    o.customer_name,
                    o_credits[o.name],
                    None,
                    _("In hand"),
                    _("PO {0}").format(o.po_no) if o.po_no else _("Advance paid"),
                )
            )
    for q in quotations:
        rows.append(evidence("Quotation", q.name, None, None, q_credits[q.name], None, _("Issued")))
    return MetricResult(
        ratio(in_hand, issued),
        in_hand,
        issued,
        _("{0} paid orders in hand / {1} quotations issued").format(round(in_hand, 2), round(issued, 2)),
        rows,
    )


# --- new clients ------------------------------------------------------------


def new_clients(ctx):
    doctype, docs, credits = _sales_docs(ctx)
    by_customer = defaultdict(float)
    first_doc = {}
    for d in sorted(docs, key=lambda d: (d.doc_date, d.name)):
        by_customer[d.customer] = max(by_customer[d.customer], credits[d.name])
        first_doc.setdefault(d.customer, d)
    existing = customer_had_orders_before(doctype, set(by_customer), ctx.start)
    count = 0.0
    rows = []
    for customer, credit in by_customer.items():
        d = first_doc[customer]
        new = customer not in existing
        count += credit if new else 0
        rows.append(
            evidence(
                doctype,
                d.name,
                d.doc_date,
                d.customer_name,
                credit,
                None,
                _("New client") if new else _("Existing client"),
            )
        )
    return MetricResult(
        count if by_customer else 0.0,
        count,
        len(by_customer),
        _("{0} new active clients out of {1} clients with orders").format(round(count, 2), len(by_customer)),
        rows,
    )


# --- sales cycle ------------------------------------------------------------


def sales_cycle_time(ctx):
    """Orders signed within the target days of first contact."""
    orders, credits = employee_sales_documents(
        ctx,
        "Sales Order",
        {"transaction_date": ["between", [ctx.start, ctx.end]]},
        ["name", "customer_name", "transaction_date", "po_date"],
    )
    limit = cint(ctx.settings.sales_cycle_days) or 60
    quotes = defaultdict(set)
    if orders:
        for item in frappe.get_all(
            "Sales Order Item",
            filters={"parent": ["in", [o.name for o in orders]], "prevdoc_docname": ["is", "set"]},
            fields=["parent", "prevdoc_docname"],
            limit_page_length=0,
        ):
            quotes[item.parent].add(item.prevdoc_docname)
    starts = {}
    all_quotes = {q for qs in quotes.values() for q in qs}
    if all_quotes:
        for q in frappe.get_all(
            "Quotation",
            filters={"name": ["in", list(all_quotes)]},
            fields=["name", "kpi_first_contact_on", "kpi_request_received_on", "creation"],
        ):
            starts[q.name] = min(
                get_datetime(x) for x in (q.kpi_first_contact_on, q.kpi_request_received_on, q.creation) if x
            )
    num = den = 0.0
    days_total = 0
    rows = []
    skipped = 0
    for o in orders:
        first = min((starts[q] for q in quotes.get(o.name, ()) if q in starts), default=None)
        if not first:
            skipped += 1
            rows.append(
                evidence(
                    "Sales Order",
                    o.name,
                    o.transaction_date,
                    o.customer_name,
                    0,
                    None,
                    _("Skipped"),
                    _("Not made from a quotation"),
                )
            )
            continue
        signed = getdate(o.po_date or o.transaction_date)
        days = max(date_diff(signed, getdate(first)), 0)
        credit = credits[o.name]
        within = days <= limit
        den += credit
        num += credit if within else 0
        days_total += days
        rows.append(
            evidence(
                "Sales Order",
                o.name,
                signed,
                o.customer_name,
                credit,
                days,
                _("Within {0} days").format(limit) if within else _("Over {0} days").format(limit),
            )
        )
    counted = len(orders) - skipped
    avg = round(days_total / counted, 1) if counted else None
    return MetricResult(
        ratio(num, den),
        num,
        den,
        _(
            "{0} of {1} orders signed within {2} days of first contact; average {3} days; {4} orders without a quotation"
        ).format(round(num, 2), round(den, 2), limit, avg if avg is not None else "-", skipped),
        rows,
    )


# --- repeat revenue ---------------------------------------------------------


def repeat_client_revenue(ctx):
    doctype, docs, credits = _sales_docs(ctx)
    repeat = customer_had_orders_before(
        doctype, {d.customer for d in docs}, ctx.start, ctx.settings.repeat_client_lookback_months
    )
    total = from_repeat = 0.0
    rows = []
    for d in docs:
        amount = flt(d.base_net_total) * credits[d.name]
        total += amount
        is_repeat = d.customer in repeat
        from_repeat += amount if is_repeat else 0
        rows.append(
            evidence(
                doctype,
                d.name,
                d.doc_date,
                d.customer_name,
                credits[d.name],
                round(amount, 2),
                _("Repeat client") if is_repeat else _("New client"),
            )
        )
    return MetricResult(
        ratio(from_repeat, total),
        round(from_repeat, 2),
        round(total, 2),
        _("{0} of {1} revenue from repeat clients").format(
            frappe.format(from_repeat, "Currency"), frappe.format(total, "Currency")
        ),
        rows,
    )


# --- records up to date -----------------------------------------------------


def records_up_to_date(ctx):
    """Deal changes and customer orders recorded within the target hours of happening."""
    hours = flt(ctx.settings.record_update_hours) or 48
    logs = frappe.get_all(
        "KPI Deal Update Log",
        filters={"employee": ctx.employee, "logged_on": ["between", [ctx.start_dt, ctx.end_dt]]},
        fields=[
            "name",
            "reference_doctype",
            "reference_name",
            "event_on",
            "logged_on",
            "lag_hours",
            "within_target",
            "update_type",
            "to_value",
        ],
        limit_page_length=0,
    )
    num = den = 0.0
    rows = []
    for log in logs:
        den += 1
        num += cint(log.within_target)
        rows.append(
            evidence(
                "KPI Deal Update Log",
                log.name,
                log.logged_on,
                log.reference_name,
                1,
                log.lag_hours,
                _("On time") if log.within_target else _("Late"),
                f"{_(log.update_type)}: {log.to_value or ''}",
            )
        )

    orders, credits = employee_sales_documents(
        ctx,
        "Sales Order",
        {"creation": ["between", [ctx.start_dt, ctx.end_dt]], "po_date": ["is", "set"]},
        ["name", "customer_name", "po_date", "creation"],
    )
    for o in orders:
        event = po_event_time(o)
        lag = max((get_datetime(o.creation) - event).total_seconds() / 3600, 0)
        within = lag <= hours
        credit = credits[o.name]
        den += credit
        num += credit if within else 0
        rows.append(
            evidence(
                "Sales Order",
                o.name,
                o.po_date,
                o.customer_name,
                credit,
                round(lag, 2),
                _("On time") if within else _("Late"),
                _("Order entered after customer PO date"),
            )
        )
    return MetricResult(
        ratio(num, den),
        num,
        den,
        _("{0} of {1} updates recorded within {2} hours").format(round(num, 2), round(den, 2), hours),
        rows,
    )
