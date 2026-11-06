# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pure date and ratio helpers of the corporate tax computations."""

import calendar

from dateutil.relativedelta import relativedelta


def is_month_end(day):
    return day.day == calendar.monthrange(day.year, day.month)[1]


def add_months(day, months):
    """Return ``day`` plus ``months`` months, the way tax deadlines count.

    A month end stays a month end: a year ending June 30 has its balance
    due two months later on August 31, not August 30. Other days keep their
    day number, clamped to the length of the target month.
    """
    target = day + relativedelta(months=months)
    if is_month_end(day):
        target += relativedelta(day=31)
    return target


def linear_ratio(value, lower, upper):
    """Return the position of ``value`` between ``lower`` and ``upper``.

    0 at or below ``lower``, 1 at or above ``upper``, linear in between.
    ``upper <= lower`` makes a step at ``upper``.
    """
    if value >= upper:
        return 1.0
    if value <= lower or upper <= lower:
        return 0.0
    return (value - lower) / (upper - lower)


def fifo_tranches(movements):
    """Split shareholder loan movements into loans repaid first-in first-out.

    ``movements`` is an iterable of ``(date, debit, credit)`` sorted by
    date, debit being money lent to the shareholder and credit a
    repayment or an amount the company owes the shareholder. Returns
    ``(tranches, credit_pool)``: each tranche is a dict with ``date``,
    ``amount`` and ``repayments`` (list of ``(date, amount)``), and
    ``credit_pool`` is what the company still owes the shareholder at the
    end. A debit first absorbs the credit pool, so an advance against an
    amount the company owes is not a loan. A credit repays the oldest
    tranche first; what remains goes to the credit pool.
    """
    tranches = []
    credit_pool = 0.0
    for day, debit, credit in movements:
        net = (debit or 0.0) - (credit or 0.0)
        if net > 0:
            absorbed = min(net, credit_pool)
            credit_pool -= absorbed
            if net - absorbed > 0:
                tranches.append(
                    {"date": day, "amount": net - absorbed, "repayments": []}
                )
        elif net < 0:
            remaining = -net
            for tranche in tranches:
                if remaining <= 0:
                    break
                open_amount = tranche_balance(tranche)
                if open_amount <= 0:
                    continue
                paid = min(open_amount, remaining)
                tranche["repayments"].append((day, paid))
                remaining -= paid
            credit_pool += remaining
    return tranches, credit_pool


def tranche_balance(tranche, day=None):
    """Return the unpaid amount of ``tranche`` at the end of ``day``.

    Without ``day``, counts every repayment. Before the tranche date the
    balance is 0.
    """
    if day is not None and day < tranche["date"]:
        return 0.0
    repaid = sum(
        amount
        for repaid_on, amount in tranche["repayments"]
        if day is None or repaid_on <= day
    )
    return tranche["amount"] - repaid
