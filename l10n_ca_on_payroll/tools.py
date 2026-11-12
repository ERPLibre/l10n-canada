# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pure helpers of the Ontario formulas of T4127 option 1."""


def lowest_rate(brackets):
    """Return the rate of the first bracket of ``brackets``.

    It is the lowest Ontario rate that K1P and K2P apply to the credit
    amounts.
    """
    return float(min((float(t), float(r)) for t, r in brackets)[1])


def surtax(basic_tax, schedule):
    """Return V1, the surtax on the basic Ontario tax ``basic_tax`` (T4).

    ``schedule`` is ``[[threshold, rate], ...]``: each threshold that
    ``basic_tax`` exceeds adds ``rate * (basic_tax - threshold)``.
    """
    return sum(
        float(rate) * (basic_tax - float(threshold))
        for threshold, rate in schedule
        if basic_tax > float(threshold)
    )


def health_premium(income, schedule):
    """Return V2, the Ontario Health Premium on the annual income ``income``.

    ``schedule`` is ``[[threshold, rate, base, maximum], ...]``: the row of
    the highest threshold that ``income`` exceeds gives
    ``min(maximum, base + rate * (income - threshold))``; an income at or
    below every threshold gives 0.
    """
    premium = 0.0
    for threshold, rate, base, maximum in sorted(
        tuple(float(value) for value in row) for row in schedule
    ):
        if income > threshold:
            premium = min(maximum, base + rate * (income - threshold))
    return premium


def tax_reduction(tax, basic_amount, dependants_amount):
    """Return S, the Ontario tax reduction of ``tax`` (T4 + V1).

    S = min(tax, 2 * (basic_amount + dependants_amount) - tax), at least
    0; ``dependants_amount`` is the factor Y.
    """
    return max(0.0, min(tax, 2 * (basic_amount + dependants_amount) - tax))
