"""Working-day arithmetic used by the quotation SLA. Pure Python, no Frappe import."""

from datetime import date, datetime, time, timedelta


def add_working_days(start, days, holidays):
    """The same clock time `days` working days after `start`.

    A request received on Thursday 10:00 with a 3 working-day SLA and a Friday/Saturday
    weekend is due on Tuesday 10:00. Holidays are skipped, never counted.
    """
    holidays = set(holidays or ())
    due = start
    counted = 0
    while counted < int(days or 0):
        due += timedelta(days=1)
        if due.date() not in holidays:
            counted += 1
    return due


def working_hours_between(start, end, holidays):
    """Elapsed hours between two datetimes, leaving out whole holiday days."""
    if not start or not end or end <= start:
        return 0.0
    holidays = set(holidays or ())
    total = timedelta()
    day = start.date()
    while day <= end.date():
        if day not in holidays:
            day_start = max(start, datetime.combine(day, time.min))
            day_end = min(end, datetime.combine(day + timedelta(days=1), time.min))
            if day_end > day_start:
                total += day_end - day_start
        day += timedelta(days=1)
    return round(total.total_seconds() / 3600.0, 2)


def hours_between(start, end):
    if not start or not end:
        return None
    return round((end - start).total_seconds() / 3600.0, 2)


def end_of_day(value):
    """A date read as the last moment of that day (lenient for date-only fields)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time(23, 59, 59))
    return value


def month_overlap_fraction(year, month, start, end):
    """Share of a calendar month that falls inside [start, end] (dates, inclusive)."""
    first = date(year, month, 1)
    last = (date(year + (month == 12), (month % 12) + 1, 1)) - timedelta(days=1)
    lo, hi = max(first, start), min(last, end)
    if hi < lo:
        return 0.0
    return ((hi - lo).days + 1) / ((last - first).days + 1)
