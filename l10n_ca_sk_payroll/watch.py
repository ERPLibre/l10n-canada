# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the Saskatchewan pages (see l10n_ca_payroll/tools/watch.py).

The Saskatchewan WCB page of the maximum assessable earnings has a table
of two rows, the years and below them their maximums, and a sentence
"The maximum assessable wage rate for YYYY is $NNN,NNN." for the year in
force. The year is read from the table; a year missing from the table but
named by the sentence is read from the sentence.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    normalize,
    tables,
)

PARAMETER = "l10n_ca.sk.wcb.max_insurable"
YEAR = re.compile(r"^\d{4}$")


def _maximums_by_year(content):
    """Return {year: maximum} of the first table whose first row holds
    only years and whose second row has as many cells."""
    for _caption, rows in tables(content):
        if len(rows) < 2 or not rows[0]:
            continue
        years, amounts = rows[0], rows[1]
        if len(years) == len(amounts) and all(YEAR.match(cell) for cell in years):
            return {
                int(year): amount(value)
                for year, value in zip(years, amounts, strict=True)
            }
    raise PageChanged("no table of the maximums by year")


def wcbsask_maximum(content, year):
    maximums = _maximums_by_year(content)
    if year in maximums:
        return {PARAMETER: maximums[year]}
    text = normalize(document(content).text_content())
    match = re.search(
        r"maximum assessable wage rate for (\d{4}) is \$([\d,]+)", text, re.IGNORECASE
    )
    if match and int(match.group(1)) == year:
        return {PARAMETER: amount(match.group(2))}
    return None


WATCHERS = {
    "wcbsask_maximum": Watcher(
        "Saskatchewan WCB - Maximum assessable earnings of the year",
        lambda year: "https://www.wcbsask.com/maximum-assessable-earnings",
        wcbsask_maximum,
    ),
}
