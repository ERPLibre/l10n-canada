# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the WSCC page for the Northwest Territories (see
l10n_ca_payroll/tools/watch.py).

The WSCC page "Employer Rates" lists the Year's Maximum Insurable
Remuneration by year in a table: one row per year, its first cell the
year and its second the figures. Since 2025 the cell gives one figure per
territory ("NWT: $116,000 - NU: $117,300"); before, one figure shared by
both. The row of the next year appears with the rates of that year, near
the end of November.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    find_table,
    year_row,
)

TERRITORY_FIGURES = re.compile(r"NWT:\s*\$\s*([\d,]+)\s*-\s*NU:\s*\$\s*([\d,]+)")
SHARED_FIGURE = re.compile(r"^\$\s*([\d,]+)$")


def wscc_ymir(content, year, territory):
    """Return the YMIR of ``territory`` ("NT" or "NU") for ``year``.

    None while the table has no row for ``year``; ``PageChanged`` when the
    page has no such table or the row reads in another format.
    """
    rows = find_table(content, header=r"NWT:\s*\$")
    row = year_row(rows, year)
    if row is None:
        return None
    if len(row) < 2:
        raise PageChanged(f"row with {len(row)} cells: {row!r}")
    match = TERRITORY_FIGURES.search(row[1])
    if match:
        return amount(match.group(1 if territory == "NT" else 2))
    match = SHARED_FIGURE.match(row[1])
    if match:
        return amount(match.group(1))
    raise PageChanged(f"no YMIR in the row of {year}: {row[1]!r}")


def wscc_ymir_nt(content, year):
    value = wscc_ymir(content, year, "NT")
    if value is None:
        return None
    return {"l10n_ca.nt.wcb.max_insurable": value}


WATCHERS = {
    "wscc_ymir_nt": Watcher(
        "WSCC - Year's Maximum Insurable Remuneration (Northwest Territories)",
        lambda year: "https://wscc.nt.ca/employer-services/employer-rates",
        wscc_ymir_nt,
    ),
}
