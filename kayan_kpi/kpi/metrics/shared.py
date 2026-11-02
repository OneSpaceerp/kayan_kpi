"""KPIs shared by both roles: the project competitor study and the margin bonus."""

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime

from kayan_kpi.kpi.common import MetricResult, employee_quotations, employee_sales_documents, evidence
from kayan_kpi.kpi.scoring import bonus_points, margin_percent, ratio

CHECKLIST = (
    "chk_competitors_identified",
    "chk_commercial_data",
    "chk_technical_comparison",
    "chk_recommendation",
)


def study_score(study, quotation_ready_on, checklist_weight):
    """Checklist (4 manager checks + on time) at `checklist_weight` %, manager rating for the rest."""
    on_time = not quotation_ready_on or get_datetime(study.creation) <= get_datetime(quotation_ready_on)
    checks = sum(cint(study.get(f)) for f in CHECKLIST) + (1 if on_time else 0)
    weight = flt(checklist_weight if checklist_weight is not None else 60)
    rating_pct = flt(study.get("manager_rating")) * 100
    return round(checks / 5 * weight + rating_pct * (100 - weight) / 100, 2), on_time


def competitor_study(ctx):
    """Average study score over the engineer's quotations; a quotation without a study scores 0."""
    filters = {"docstatus": 1, "transaction_date": ["between", [ctx.start, ctx.end]]}
    if flt(ctx.settings.competitor_study_min_value):
        filters["base_net_total"] = [">=", flt(ctx.settings.competitor_study_min_value)]
    quotations, credits = employee_quotations(
        ctx, filters, ["name", "customer_name", "transaction_date", "kpi_ready_on"]
    )
    if not quotations:
        return MetricResult(None, details=_("No quotations needing a competitor study"))

    studies = frappe.get_all(
        "Competitor Study",
        filters={"docstatus": 1, "quotation": ["in", [q.name for q in quotations]]},
        fields=["name", "quotation", "kpi_role", "creation", "manager_rating", *CHECKLIST],
        limit_page_length=0,
    )
    by_quotation = {}
    for s in studies:
        by_quotation.setdefault(s.quotation, []).append(s)

    weight = ctx.settings.competitor_checklist_weight
    total = den = 0.0
    missing = 0
    rows = []
    for q in quotations:
        credit = credits[q.name]
        den += credit
        candidates = by_quotation.get(q.name, [])
        candidates = [s for s in candidates if s.kpi_role == ctx.role] or candidates
        if not candidates:
            missing += 1
            rows.append(
                evidence("Quotation", q.name, q.transaction_date, q.customer_name, credit, 0, _("No study"))
            )
            continue
        scored = [(study_score(s, q.kpi_ready_on, weight), s) for s in candidates]
        (score, on_time), best = max(scored, key=lambda x: x[0][0])
        total += score * credit
        rows.append(
            evidence(
                "Competitor Study",
                best.name,
                q.transaction_date,
                q.customer_name,
                credit,
                score,
                _("On time") if on_time else _("Late"),
                q.name,
            )
        )
    avg = round(total / den, 4) if den else None
    return MetricResult(
        avg,
        round(total / 100, 2),
        den,
        _("Average study score {0}% over {1} quotations; {2} without a study").format(
            round(avg or 0, 1), round(den, 2), missing
        ),
        rows,
    )


def _document_cost(doctype, name, settings):
    item_doctype = "Sales Invoice Item" if doctype == "Sales Invoice" else "Sales Order Item"
    rate_field = "incoming_rate" if doctype == "Sales Invoice" else "valuation_rate"
    items = frappe.get_all(
        item_doctype,
        filters={"parent": name},
        fields=["qty", "stock_qty", "kpi_estimated_cost", rate_field],
        limit_page_length=0,
    )
    source = settings.cost_source or "Estimated Cost, else Valuation Rate"
    cost = 0.0
    missing = 0
    for item in items:
        estimated = flt(item.kpi_estimated_cost) * flt(item.qty)
        valued = flt(item.get(rate_field)) * flt(item.stock_qty)
        if source == "Estimated Cost Only":
            line = estimated
        elif source == "Valuation Rate Only":
            line = valued
        else:
            line = estimated or valued
        if not line:
            missing += 1
        cost += line
    return cost, missing


def margin_bonus(ctx):
    """Bonus points for deals above the margin threshold. Kept outside the 100% weights."""
    settings = ctx.settings
    doctype = settings.sales_basis or "Sales Order"
    date_field = "posting_date" if doctype == "Sales Invoice" else "transaction_date"
    filters = {date_field: ["between", [ctx.start, ctx.end]]}
    if doctype == "Sales Invoice":
        filters["is_return"] = 0
    docs, credits = employee_sales_documents(
        ctx, doctype, filters, ["name", "customer_name", date_field, "base_net_total"]
    )
    points = 0.0
    qualified = 0
    rows = []
    for d in docs:
        cost, missing = _document_cost(doctype, d.name, settings)
        margin = margin_percent(d.base_net_total, cost, settings.margin_basis)
        deal_points = (
            bonus_points(
                margin,
                settings.margin_threshold_percent,
                settings.bonus_method,
                settings.bonus_points_per_percent,
                settings.bonus_fixed_points,
            )
            * credits[d.name]
        )
        points += deal_points
        qualified += 1 if deal_points else 0
        note = _("{0} items without cost").format(missing) if missing else None
        rows.append(
            evidence(
                doctype,
                d.name,
                d.get(date_field),
                d.customer_name,
                credits[d.name],
                margin,
                round(deal_points, 2),
                note,
            )
        )
    return MetricResult(
        round(points, 2),
        qualified,
        len(docs),
        _("{0} of {1} deals above {2}% margin").format(
            qualified, len(docs), flt(settings.margin_threshold_percent)
        ),
        rows,
    )
