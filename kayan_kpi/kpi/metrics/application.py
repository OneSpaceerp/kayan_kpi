"""Application Engineer KPIs (Goals for Application Engineers, Q3-Q4)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_datetime, getdate, nowdate

from kayan_kpi.kpi.common import WON_STATUSES, MetricResult, employee_quotations, evidence
from kayan_kpi.kpi.scoring import ratio
from kayan_kpi.kpi.sources import compute_due


def quote_turnaround(ctx):
    """Quotations ready to send within the SLA, as % of quotations made ready in the period."""
    quotations, credits = employee_quotations(
        ctx,
        {"docstatus": 1, "kpi_ready_on": ["between", [ctx.start_dt, ctx.end_dt]]},
        [
            "name",
            "customer_name",
            "company",
            "kpi_request_received_on",
            "kpi_inquiry_complexity",
            "kpi_agreed_due_on",
            "kpi_due_on",
            "kpi_ready_on",
            "kpi_tat_hours",
        ],
    )
    num = den = 0.0
    rows = []
    for q in quotations:
        credit = credits[q.name]
        due = q.kpi_due_on or compute_due(
            q.kpi_request_received_on, q.kpi_inquiry_complexity, q.kpi_agreed_due_on, q.company
        )
        if not due:
            rows.append(
                evidence(
                    "Quotation",
                    q.name,
                    q.kpi_ready_on,
                    q.customer_name,
                    0,
                    None,
                    _("Skipped"),
                    _("No request time"),
                )
            )
            continue
        on_time = get_datetime(q.kpi_ready_on) <= get_datetime(due)
        den += credit
        num += credit if on_time else 0
        rows.append(
            evidence(
                "Quotation",
                q.name,
                q.kpi_ready_on,
                q.customer_name,
                credit,
                q.kpi_tat_hours,
                _("On time") if on_time else _("Late"),
                _("{0} inquiry, due {1}").format(_(q.kpi_inquiry_complexity or "Standard"), due),
            )
        )
    return MetricResult(
        ratio(num, den),
        num,
        den,
        _("{0} of {1} quotations ready within the SLA").format(round(num, 2), round(den, 2)),
        rows,
    )


def _latest_reviews(ctx):
    reviews = frappe.get_all(
        "Technical Review",
        filters={"docstatus": 1, "review_date": ["between", [ctx.start, ctx.end]]},
        fields=[
            "name",
            "quotation",
            "review_date",
            "selection_result",
            "standards_result",
            "customer_name",
            "quotation_status",
            "creation",
        ],
        order_by="review_date desc, creation desc",
        limit_page_length=0,
    )
    latest = {}
    for r in reviews:
        latest.setdefault(r.quotation, r)
    return latest


def _review_metric(ctx, field, passed_value, label):
    latest = _latest_reviews(ctx)
    if not latest:
        return MetricResult(None, details=_("No technical reviews in the period"))
    quotations, credits = employee_quotations(ctx, {"name": ["in", list(latest)]}, ["name", "status"])
    ordered_only = ctx.settings.selection_accuracy_scope == "Ordered Quotations Only"
    num = den = 0.0
    rows = []
    for q in quotations:
        review = latest[q.name]
        credit = credits[q.name]
        if ordered_only and q.status not in WON_STATUSES:
            rows.append(
                evidence(
                    "Technical Review",
                    review.name,
                    review.review_date,
                    review.customer_name,
                    0,
                    review.get(field),
                    _("Skipped"),
                    _("Quotation not ordered (not in hand)"),
                )
            )
            continue
        passed = review.get(field) == passed_value
        den += credit
        num += credit if passed else 0
        rows.append(
            evidence(
                "Technical Review",
                review.name,
                review.review_date,
                review.customer_name,
                credit,
                review.get(field),
                _("Pass") if passed else _("Fail"),
                q.name,
            )
        )
    return MetricResult(
        ratio(num, den),
        num,
        den,
        _("{0} of {1} reviewed selections {2}").format(round(num, 2), round(den, 2), label),
        rows,
    )


def selection_accuracy(ctx):
    return _review_metric(ctx, "selection_result", "Passed - No Correction", _("passed with no correction"))


def standards_compliance(ctx):
    return _review_metric(ctx, "standards_result", "Compliant", _("met the required standards"))


def client_query_service(ctx):
    """Half reply-on-time rate, half client rating against the target rating."""
    queries = frappe.get_all(
        "Technical Query",
        filters={"employee": ctx.employee, "received_on": ["between", [ctx.start_dt, ctx.end_dt]]},
        fields=[
            "name",
            "subject",
            "customer",
            "received_on",
            "first_reply_on",
            "replied_on_time",
            "client_rating",
        ],
        limit_page_length=0,
    )
    reply_hours = flt(ctx.settings.query_reply_hours) or 24
    target_rating = flt(ctx.settings.target_client_rating) or 4.5
    now = get_datetime()
    on_time = counted = 0
    ratings = []
    rows = []
    for q in queries:
        deadline_passed = (now - get_datetime(q.received_on)).total_seconds() / 3600 > reply_hours
        if q.first_reply_on or deadline_passed:
            counted += 1
            on_time += cint(q.replied_on_time)
            result = _("On time") if q.replied_on_time else _("Late")
        else:
            result = _("Waiting")
        rating = round(flt(q.client_rating) * 5, 2) if q.client_rating else None
        if rating is not None:
            ratings.append(rating)
        rows.append(
            evidence("Technical Query", q.name, q.received_on, q.customer, 1, rating, result, q.subject)
        )

    reply_rate = ratio(on_time, counted)
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    parts = [p for p in (reply_rate, avg_rating and avg_rating / target_rating * 100) if p is not None]
    actual = round(sum(parts) / len(parts), 4) if parts else None
    details = _("Replied on time: {0}; average rating: {1} of 5 (target {2})").format(
        f"{on_time}/{counted}" if counted else "-",
        avg_rating if avg_rating is not None else "-",
        target_rating,
    )
    return MetricResult(actual, on_time, counted, details, rows)


def quotation_win_rate(ctx):
    """Quotations issued in the period that became an order."""
    quotations, credits = employee_quotations(
        ctx,
        {"docstatus": 1, "transaction_date": ["between", [ctx.start, ctx.end]]},
        ["name", "customer_name", "transaction_date", "status", "base_net_total"],
    )
    num = den = 0.0
    rows = []
    for q in quotations:
        credit = credits[q.name]
        won = q.status in WON_STATUSES
        den += credit
        num += credit if won else 0
        rows.append(
            evidence(
                "Quotation",
                q.name,
                q.transaction_date,
                q.customer_name,
                credit,
                q.base_net_total,
                _("Won") if won else _(q.status),
            )
        )
    return MetricResult(
        ratio(num, den), num, den, _("{0} of {1} quotations won").format(round(num, 2), round(den, 2)), rows
    )


def required_document_types(settings):
    required = []
    if cint(settings.require_datasheet):
        required.append("Datasheet")
    if cint(settings.require_calculation):
        required.append("Calculation")
    return required


def paperwork_complete(ctx):
    """Submitted quotations with every required document, counting stale drafts as incomplete."""
    required = required_document_types(ctx.settings)
    submitted, credits = employee_quotations(
        ctx,
        {"docstatus": 1, "transaction_date": ["between", [ctx.start, ctx.end]]},
        ["name", "customer_name", "transaction_date"],
    )
    as_of = min(getdate(ctx.end), getdate(nowdate()))
    draft_cutoff = add_days(as_of, -cint(ctx.settings.draft_age_days or 7))
    drafts, draft_credits = employee_quotations(
        ctx,
        {"docstatus": 0, "creation": ["between", [ctx.start_dt, get_datetime(f"{draft_cutoff} 23:59:59")]]},
        ["name", "customer_name", "creation"],
    )
    docs = {}
    if submitted:
        for row in frappe.get_all(
            "KPI Quotation Document",
            filters={"parenttype": "Quotation", "parent": ["in", [q.name for q in submitted]]},
            fields=["parent", "document_type", "attachment"],
            limit_page_length=0,
        ):
            if row.attachment:
                docs.setdefault(row.parent, set()).add(row.document_type)

    num = den = 0.0
    rows = []
    for q in submitted:
        credit = credits[q.name]
        missing = [d for d in required if d not in docs.get(q.name, set())]
        den += credit
        num += 0 if missing else credit
        rows.append(
            evidence(
                "Quotation",
                q.name,
                q.transaction_date,
                q.customer_name,
                credit,
                None,
                _("Complete") if not missing else _("Incomplete"),
                _("Missing: {0}").format(", ".join(_(m) for m in missing)) if missing else None,
            )
        )
    for d in drafts:
        credit = draft_credits[d.name]
        den += credit
        age = date_diff(as_of, getdate(d.creation))
        rows.append(
            evidence(
                "Quotation",
                d.name,
                getdate(d.creation),
                d.customer_name,
                credit,
                age,
                _("Draft"),
                _("Draft for {0} days").format(age),
            )
        )
    return MetricResult(
        ratio(num, den),
        num,
        den,
        _("{0} of {1} quotations complete ({2} stale drafts)").format(
            round(num, 2), round(den, 2), len(drafts)
        ),
        rows,
    )
