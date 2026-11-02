import unittest
from datetime import date, datetime

from kayan_kpi.kpi.scoring import (
    EXCLUDE,
    FULL,
    PASS_FAIL,
    ZERO,
    ScoredRow,
    achievement,
    bonus_points,
    margin_percent,
    ratio,
    total_score,
)
from kayan_kpi.kpi.working_days import (
    add_working_days,
    end_of_day,
    month_overlap_fraction,
    working_hours_between,
)


class TestAchievement(unittest.TestCase):
    def test_linear(self):
        self.assertEqual(achievement(90, 100), 90)
        self.assertEqual(achievement(30, 30), 100)

    def test_over_achievement_capped(self):
        self.assertEqual(achievement(150, 100, cap=120), 120)
        self.assertEqual(achievement(110, 100, cap=120), 110)

    def test_over_achievement_disabled(self):
        self.assertEqual(achievement(150, 100, allow_over=False, cap=120), 100)

    def test_pass_fail(self):
        self.assertEqual(achievement(99.9, 100, method=PASS_FAIL), 0)
        self.assertEqual(achievement(100, 100, method=PASS_FAIL), 100)

    def test_count_target(self):
        # 2 new clients against a target of 3
        self.assertAlmostEqual(achievement(2, 3), 66.6667, places=3)

    def test_never_negative(self):
        self.assertEqual(achievement(-10, 100), 0)


class TestTotals(unittest.TestCase):
    def rows(self):
        return [ScoredRow(25, 100), ScoredRow(25, 80), ScoredRow(50, None)]

    def test_exclude_and_reweight(self):
        rows = self.rows()
        total, weight = total_score(rows, EXCLUDE)
        self.assertEqual(weight, 50)
        self.assertEqual(total, 90)
        self.assertEqual(rows[2].weighted_score, 0)
        self.assertAlmostEqual(sum(r.weighted_score for r in rows), total)

    def test_zero(self):
        total, weight = total_score(self.rows(), ZERO)
        self.assertEqual(weight, 100)
        self.assertEqual(total, 45)

    def test_full(self):
        total, _ = total_score(self.rows(), FULL)
        self.assertEqual(total, 95)

    def test_over_100_total_possible(self):
        total, _ = total_score([ScoredRow(50, 120), ScoredRow(50, 110)])
        self.assertEqual(total, 115)


class TestHelpers(unittest.TestCase):
    def test_ratio(self):
        self.assertIsNone(ratio(1, 0))
        self.assertEqual(ratio(3, 10), 30)

    def test_margin(self):
        self.assertEqual(margin_percent(100, 40), 60)
        self.assertEqual(margin_percent(100, 40, "Markup on Cost"), 150)
        self.assertIsNone(margin_percent(100, 0))

    def test_bonus(self):
        self.assertEqual(bonus_points(60, 50, "Points per % Above Threshold", 2), 20)
        self.assertEqual(bonus_points(60, 50, "Points per % of Final Margin", 1), 60)
        self.assertEqual(bonus_points(60, 50, "Fixed Points per Deal", fixed_points=5), 5)
        self.assertEqual(bonus_points(50, 50, "Fixed Points per Deal", fixed_points=5), 0)


class TestWorkingDays(unittest.TestCase):
    # Friday 2026-10-02 and Saturday 2026-10-03 are the weekend; 2026-10-06 a holiday
    holidays = {date(2026, 10, 2), date(2026, 10, 3), date(2026, 10, 6)}

    def test_three_working_days_skip_weekend_and_holiday(self):
        start = datetime(2026, 10, 1, 10, 0)  # Thursday
        due = add_working_days(start, 3, self.holidays)
        # Sun 4, Mon 5, (Tue 6 holiday), Wed 7
        self.assertEqual(due, datetime(2026, 10, 7, 10, 0))

    def test_no_holidays(self):
        self.assertEqual(add_working_days(datetime(2026, 10, 1, 9), 3, set()), datetime(2026, 10, 4, 9))

    def test_working_hours(self):
        start = datetime(2026, 10, 1, 12, 0)
        end = datetime(2026, 10, 4, 12, 0)
        # Thu 12h + Fri/Sat skipped + Sun 12h
        self.assertEqual(working_hours_between(start, end, self.holidays), 24)

    def test_end_of_day(self):
        self.assertEqual(end_of_day(date(2026, 1, 1)), datetime(2026, 1, 1, 23, 59, 59))

    def test_month_overlap(self):
        self.assertEqual(month_overlap_fraction(2026, 9, date(2026, 7, 1), date(2026, 9, 30)), 1)
        self.assertEqual(month_overlap_fraction(2026, 10, date(2026, 7, 1), date(2026, 9, 30)), 0)
        self.assertAlmostEqual(month_overlap_fraction(2026, 9, date(2026, 9, 16), date(2026, 9, 30)), 0.5)


if __name__ == "__main__":
    unittest.main()
