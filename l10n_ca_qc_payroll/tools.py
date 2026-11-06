# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pure helpers of the Revenu Quebec formulas (TP-1015.F)."""

import math
from decimal import ROUND_HALF_UP, Decimal

from odoo.addons.l10n_ca_time_parameter.tools import bracket_constant


def round_half_up(amount, digits=2):
    """Round ``amount`` to ``digits`` decimals, a half going up.

    The Revenu Quebec formulas round a fraction of 0.005 up to the next
    cent and a rate whose third decimal is 5 up to the next hundredth. The
    amount goes through ``repr`` so that a float such as 2.675 is rounded
    as written, not as its binary approximation.
    """
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(repr(round(amount, 9))).quantize(quantum, ROUND_HALF_UP))


def quebec_constant(amount, brackets):
    """Return the constant K of the Quebec bracket of ``amount``.

    K is derived from the bracket table like the federal constant, then
    truncated to the dollar: the table of TP-1015.F-V shows 2,717 for
    54,345 x 0.05 = 2,717.25 and 10,465 for 10,465.54.
    """
    return float(math.floor(round(bracket_constant(amount, brackets), 6)))


def hsf_rate(total_payroll, formula, payroll_min, payroll_max):
    """Return the Health Services Fund rate, in percent, of a total payroll.

    ``formula`` is the ``[a, b]`` pair of the employer sector: the rate is
    ``a + b * S``, S being the total payroll in millions bounded by
    ``payroll_min`` and ``payroll_max``, rounded half up to two decimals.
    """
    base, slope = (float(value) for value in formula)
    payroll = min(max(float(total_payroll or 0.0), payroll_min), payroll_max)
    return round_half_up(base + slope * payroll / 1_000_000)
