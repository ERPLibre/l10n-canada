# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Date arithmetic of the tax calendar, without database access."""

import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

# Sub-periods of a month for each period type that splits months, as
# (first day, last day) with 31 meaning the last day of the month.
MONTH_SPLITS = {
    "month": [(1, 31)],
    "semi_month": [(1, 15), (16, 31)],
    "quarter_month": [(1, 7), (8, 14), (15, 21), (22, 31)],
}


def month_end(day):
    """Return the last day of the month of ``day``."""
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def add_months(day, months):
    """Add ``months`` to ``day``, keeping the end of the month.

    "One month after March 31" is April 30 and "three months after
    February 28" is May 31: a date that ends its month lands on the last day
    of the target month, as the tax statutes count periods.
    """
    result = day + relativedelta(months=months)
    if day == month_end(day):
        result = month_end(result)
    return result


def fixed_date(year, month, day):
    """Return ``date(year, month, day)``; a day past the month end is its last day."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def calendar_periods(period_type, date_from, date_to):
    """Yield the calendar periods ``(start, end)`` whose end is in the range.

    ``period_type`` is one of ``month``, ``semi_month``, ``quarter_month``,
    ``quarter`` or ``year``; quarters and years follow the calendar year.
    """
    if period_type == "year":
        for year in range(date_from.year, date_to.year + 1):
            yield date(year, 1, 1), date(year, 12, 31)
        return
    if period_type == "quarter":
        start = date(date_from.year, 3 * ((date_from.month - 1) // 3) + 1, 1)
        while start <= date_to:
            end = month_end(start + relativedelta(months=2))
            if end >= date_from:
                yield start, end
            start = end + timedelta(days=1)
        return
    splits = MONTH_SPLITS[period_type]
    month = date_from.replace(day=1)
    while month <= date_to:
        last = month_end(month).day
        for first_day, last_day in splits:
            start = month.replace(day=first_day)
            end = month.replace(day=min(last_day, last))
            if date_from <= end <= date_to:
                yield start, end
        month += relativedelta(months=1)


def fiscal_periods(fiscal_year_dates, months, date_from, date_to):
    """Yield the fiscal periods ``(start, end)`` whose end is in the range.

    ``fiscal_year_dates(day)`` returns ``(first, last)`` of the fiscal year
    containing ``day``. Each fiscal year is cut in periods of ``months``
    months from its first day; the last period stops at the fiscal year end
    when the year is not a multiple of ``months`` long.
    """
    start, _last = fiscal_year_dates(date_from)
    while start <= date_to:
        _first, year_end = fiscal_year_dates(start)
        index = 0
        period_start = start
        while period_start <= year_end:
            index += 1
            period_end = min(
                start + relativedelta(months=months * index) - timedelta(days=1),
                year_end,
            )
            if date_from <= period_end <= date_to:
                yield period_start, period_end
            period_start = period_end + timedelta(days=1)
        start = year_end + timedelta(days=1)


class BusinessCalendar:
    """Business days of one jurisdiction: no Saturday, Sunday or holiday.

    ``holidays_of_year(year)`` returns the set of holiday dates of a year;
    it is called once per year the calendar reaches.
    """

    def __init__(self, holidays_of_year):
        self._holidays_of_year = holidays_of_year
        self._years = {}

    def is_business_day(self, day):
        if day.weekday() >= 5:
            return False
        if day.year not in self._years:
            self._years[day.year] = set(self._holidays_of_year(day.year))
        return day not in self._years[day.year]

    def next_business_day(self, day):
        """Return ``day`` if it is a business day, else the next one."""
        while not self.is_business_day(day):
            day += timedelta(days=1)
        return day

    def add_business_days(self, day, count):
        """Return the ``count``-th business day after ``day``."""
        for _index in range(count):
            day = self.next_business_day(day + timedelta(days=1))
        return day
