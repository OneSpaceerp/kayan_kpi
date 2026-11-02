"""Builds and scores KPI Scorecards."""

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from kayan_kpi.kpi.common import SALES, MetricContext, get_settings
from kayan_kpi.kpi.metrics import MANUAL, run_metric
from kayan_kpi.kpi.metrics.shared import margin_bonus
from kayan_kpi.kpi.scoring import ScoredRow, achievement, total_score


def make_context(employee, period_name, role, target=0.0):
    period = frappe.get_cached_doc("KPI Period", period_name)
    return MetricContext(
        employee=employee,
        role=role,
        start=period.start_date,
        end=period.end_date,
        settings=get_settings(),
        company=period.company or frappe.db.get_value("Employee", employee, "company"),
        period=period.name,
        target=flt(target),
    )


def _row_key(goal, metric):
    return f"{goal}::{metric}"


def calculate(scorecard):
    """Re-run every KPI on the scorecard from live data. Manager overrides are kept."""
    template = frappe.get_cached_doc("KPI Template", scorecard.kpi_template)
    role = template.kpi_role
    overrides = {
        _row_key(r.goal, r.metric): r
        for r in scorecard.get("items") or []
        if cint(r.override) or r.data_source != "Automatic"
    }

    scorecard.set("items", [])
    for t in template.items:
        ctx = make_context(scorecard.employee, scorecard.kpi_period, role, t.target_value)
        result = run_metric(t.metric, ctx)
        previous = overrides.get(_row_key(t.goal, t.metric))
        scorecard.append(
            "items",
            {
                "goal": t.goal,
                "metric": t.metric,
                "target_value": t.target_value,
                "uom": t.uom,
                "scoring_method": t.scoring_method,
                "weight": t.weight,
                "kra": t.kra,
                "actual_value": result.actual,
                "has_data": 1 if result.actual is not None else 0,
                "numerator": result.numerator,
                "denominator": result.denominator,
                "details": result.details,
                "data_source": (previous.data_source if previous else None)
                or ("Manual" if t.metric == MANUAL else "Automatic"),
                "override": previous.override if previous else 0,
                "override_actual": previous.override_actual if previous else None,
                "override_reason": previous.override_reason if previous else None,
            },
        )

    scorecard.bonus_points = 0
    settings = get_settings()
    if role == SALES and cint(settings.enable_margin_bonus):
        bonus = margin_bonus(make_context(scorecard.employee, scorecard.kpi_period, role))
        scorecard.bonus_points = bonus.actual or 0

    scorecard.last_calculated_on = now_datetime()
    if scorecard.status == "Draft":
        scorecard.status = "Calculated"
    apply_scoring(scorecard)


def apply_scoring(scorecard):
    """Achievement, weighted score and totals from the rows as they stand (overrides included)."""
    settings = get_settings()
    scored = []
    for row in scorecard.get("items") or []:
        if cint(row.override):
            actual, has_data = row.override_actual, True
        else:
            actual, has_data = row.actual_value, bool(cint(row.has_data)) and row.metric != MANUAL
        value = (
            achievement(
                actual,
                row.target_value,
                row.scoring_method or "Linear",
                cint(settings.allow_over_achievement),
                flt(settings.max_achievement_percent) or 100,
            )
            if has_data
            else None
        )
        scored.append(ScoredRow(flt(row.weight), value))

    total, weight = total_score(scored, settings.no_data_rule or "Exclude and Re-weight")
    for row, s in zip(scorecard.get("items") or [], scored, strict=True):
        row.achievement_percent = s.achievement if s.achievement is not None else 0
        row.weighted_score = s.weighted_score

    scorecard.total_weight = sum(flt(r.weight) for r in scorecard.get("items") or [])
    scorecard.scored_weight = weight
    scorecard.total_score = total


def evidence_for(employee, period, metric, role=None):
    """Document-level rows behind one KPI, for the KPI Evidence report."""
    if not role:
        template = frappe.db.get_value("Employee", employee, "kpi_template")
        role = frappe.db.get_value("KPI Template", template, "kpi_role") if template else None
    if not role:
        frappe.throw(_("Choose a KPI Role or set a KPI Template on the employee."))
    ctx = make_context(employee, period, role)
    if metric == "Margin Bonus":
        return margin_bonus(ctx)
    return run_metric(metric, ctx)
