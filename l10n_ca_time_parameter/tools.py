# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pure helpers for bracket tables stored as JSON time parameters.

A bracket table is a list of ``[threshold, rate]`` pairs sorted by
threshold, the first threshold being 0: ``[[0, 0.14], [58523, 0.205]]``
taxes the first 58,523 at 14% and the rest at 20.5%.
"""


def _sorted_brackets(brackets):
    if not brackets:
        raise ValueError("Empty bracket table")
    table = sorted((float(t), float(r)) for t, r in brackets)
    if table[0][0] != 0.0:
        raise ValueError("A bracket table must start at threshold 0")
    return table


def progressive_tax(amount, brackets):
    """Return the tax on ``amount`` for a progressive bracket table.

    Negative amounts return 0. Equals ``R * A - K`` of the CRA and Revenu
    Quebec payroll formulas, K being the bracket constant.
    """
    if amount <= 0:
        return 0.0
    table = _sorted_brackets(brackets)
    tax = 0.0
    for index, (threshold, rate) in enumerate(table):
        upper = table[index + 1][0] if index + 1 < len(table) else None
        if amount <= threshold:
            break
        taxed = (min(amount, upper) if upper is not None else amount) - threshold
        tax += taxed * rate
    return tax


def marginal_rate(amount, brackets):
    """Return the rate of the bracket that contains ``amount``."""
    table = _sorted_brackets(brackets)
    rate = table[0][1]
    for threshold, bracket_rate in table:
        if amount > threshold or threshold == 0.0:
            rate = bracket_rate
    return rate


def bracket_constant(amount, brackets):
    """Return K such that ``progressive_tax(A) == marginal_rate(A) * A - K``."""
    return marginal_rate(amount, brackets) * amount - progressive_tax(
        amount, brackets
    )
