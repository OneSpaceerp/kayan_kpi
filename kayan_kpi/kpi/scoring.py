"""Turns KPI actuals into achievement % and a weighted total.

Pure Python on purpose: no Frappe import, so the rules can be unit tested anywhere.
"""

from dataclasses import dataclass

LINEAR = "Linear"
PASS_FAIL = "Pass/Fail"

EXCLUDE = "Exclude and Re-weight"
ZERO = "Score as Zero"
FULL = "Full Score"


def achievement(actual, target, method=LINEAR, allow_over=True, cap=120.0):
    """Achievement % of `actual` against `target`, where higher is better.

    Every metric reports a "higher is better" actual (turnaround is reported as
    % of quotations on time, not as hours), so one rule covers all of them.
    """
    actual = float(actual or 0)
    target = float(target or 0)

    if method == PASS_FAIL:
        value = 100.0 if actual >= target else 0.0
    elif target <= 0:
        value = 100.0
    else:
        value = actual / target * 100.0

    limit = float(cap or 100) if allow_over else 100.0
    return round(max(0.0, min(value, max(limit, 100.0))), 4)


@dataclass
class ScoredRow:
    weight: float
    achievement: float | None  # None when the KPI had no data
    weighted_score: float = 0.0
    counted: bool = True


def total_score(rows, no_data_rule=EXCLUDE):
    """Fill `weighted_score` on each row and return (total %, weight that was scored).

    `weighted_score` is the row's contribution in percentage points, so the rows add
    up to the total. With "Exclude and Re-weight", rows without data are left out and
    the remaining weights are scaled back up to the full weight.
    """
    considered_weight = 0.0
    for row in rows:
        if row.achievement is None:
            if no_data_rule == EXCLUDE:
                row.counted = False
                continue
            row.achievement = 0.0 if no_data_rule == ZERO else 100.0
        row.counted = True
        considered_weight += float(row.weight or 0)

    total = 0.0
    for row in rows:
        if not row.counted or not considered_weight:
            row.weighted_score = 0.0
            continue
        row.weighted_score = round(row.achievement * float(row.weight or 0) / considered_weight, 4)
        total += row.weighted_score

    return round(total, 2), round(considered_weight, 4)


def ratio(numerator, denominator):
    """Percentage, or None when there is nothing to measure."""
    if not denominator:
        return None
    return round(float(numerator) / float(denominator) * 100.0, 4)


def margin_percent(net, cost, basis="Margin on Selling Price"):
    """Margin on selling price, or markup on cost. None when it cannot be measured."""
    net = float(net or 0)
    cost = float(cost or 0)
    if cost <= 0:
        return None
    if basis == "Markup on Cost":
        return round((net - cost) / cost * 100.0, 4)
    if net <= 0:
        return None
    return round((net - cost) / net * 100.0, 4)


def bonus_points(margin, threshold, method, points_per_percent=1.0, fixed_points=0.0):
    """Bonus points for one deal. Zero unless the margin is above the threshold."""
    if margin is None or margin <= float(threshold or 0):
        return 0.0
    if method == "Fixed Points per Deal":
        return float(fixed_points or 0)
    if method == "Points per % of Final Margin":
        return round(margin * float(points_per_percent or 0), 4)
    return round((margin - float(threshold or 0)) * float(points_per_percent or 0), 4)
