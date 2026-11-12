# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the Newfoundland and Labrador pages (see
l10n_ca_payroll/tools/watch.py).

The WorkplaceNL "Annual Assessment" page has a table of the maximum
assessable earnings without caption: a first row of years, a second row of
amounts in the same columns. The year announced for January 1 joins the
table in November; until then the next year is "not yet published".
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import PageChanged, Watcher, amount, tables

YEAR = re.compile(r"^\d{4}$")


def workplacenl_maximum(content, year):
    """Return the maximum assessable earnings of ``year``, or None.

    Reads the first table whose first row holds only years; the amount of
    ``year`` is the cell of the second row in the column of that year.
    """
    for _caption, rows in tables(content):
        if len(rows) < 2 or not rows[0] or not all(YEAR.match(c) for c in rows[0]):
            continue
        years = [int(cell) for cell in rows[0]]
        if len(rows[1]) != len(years):
            raise PageChanged(f"{len(rows[1])} amounts for {len(years)} years")
        if year not in years:
            return None
        return {"l10n_ca.nl.wcb.max_insurable": amount(rows[1][years.index(year)])}
    raise PageChanged("no table of the maximum assessable earnings by year")


WATCHERS = {
    "workplacenl_maximum": Watcher(
        "WorkplaceNL - Maximum assessable earnings by year (Annual Assessment)",
        lambda year: (
            "https://workplacenl.ca/employers/manage-my-account/annual-assessment/"
        ),
        workplacenl_maximum,
    ),
}
