# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Helpers for the capital cost allowance parameters.

An eligibility window table is a JSON list of objects. Each object may
bound the acquisition date (``acquired_from`` / ``acquired_to``) and the
available-for-use date (``available_from`` / ``available_to``), all
inclusive ISO dates, and carries one or more numeric values::

    [{"acquired_from": "2025-01-01", "available_to": "2029-12-31",
      "hyr": 3.0, "no_hyr": 1.5}]

A missing bound is open. When several windows match, the largest value
wins: the enhancements of successive budgets overlap and a taxpayer
always gets the most favourable one that applies.
"""

from odoo.fields import Date

from odoo.addons.l10n_ca_time_parameter.models.res_company import _NO_DEFAULT

PARAM_PREFIX = "l10n_ca.cca."
QUEBEC_PREFIX = "l10n_ca.cca.qc."


def _window_matches(window, acquired, available):
    for key, value in (("acquired", acquired), ("available", available)):
        lower = window.get(f"{key}_from")
        upper = window.get(f"{key}_to")
        if lower and (not value or value < Date.to_date(lower)):
            return False
        if upper and (not value or value > Date.to_date(upper)):
            return False
    return True


def window_value(windows, acquired, available, key):
    """Return the largest ``key`` value of the windows matching the dates.

    Returns 0.0 when no window matches or ``windows`` is empty, so a
    missing enhancement reads as "no enhancement".
    """
    values = [
        float(window.get(key) or 0.0)
        for window in windows or []
        if _window_matches(window, acquired, available)
    ]
    return max(values) if values else 0.0


def cca_param(company, key, date, jurisdiction="federal", default=_NO_DEFAULT):
    """Read the CCA parameter ``l10n_ca.cca.<key>`` for ``company``.

    For the Quebec jurisdiction, ``l10n_ca.cca.qc.<key>`` is read first and
    the federal parameter applies when it does not exist: Quebec follows
    the federal classes and rates unless a Quebec parameter says otherwise.
    """
    if jurisdiction == "quebec":
        missing = object()
        value = company._l10n_ca_param(QUEBEC_PREFIX + key, date, default=missing)
        if value is not missing:
            return value
    return company._l10n_ca_param(PARAM_PREFIX + key, date, default=default)
