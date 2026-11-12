# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the Nova Scotia pages (see l10n_ca_payroll/tools/watch.py).

The WCB Nova Scotia page of the maximum assessable earnings states the
maximum of its latest year in one sentence ("The maximum assessable
earnings for 2027 is $83,300.") and the earlier years in a table by year.
The board publishes the next year's maximum before the end of the current
year: the sentence then names the next year and the current year moves to
the table.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    find_table,
    normalize,
    year_row,
)

CODE = "l10n_ca.ns.wcb.max_insurable"


def wcb_ns_maximum(content, year):
    """Return the maximum assessable earnings of ``year`` read on the page.

    The sentence gives the latest year; a later year is not published yet
    (None); an earlier year is read in the table of the previous years,
    None when the table lacks it.
    """
    text = normalize(document(content).text_content())
    match = re.search(
        r"The maximum assessable earnings for (\d{4}) is \$([\d,]+)",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise PageChanged("no maximum assessable earnings sentence")
    latest = int(match.group(1))
    if year == latest:
        return {CODE: amount(match.group(2))}
    if year > latest:
        return None
    row = year_row(find_table(content, header=r"Maximum Assessable Earnings"), year)
    if row is None:
        return None
    if len(row) < 2:
        raise PageChanged(f"row with {len(row)} cells: {row!r}")
    return {CODE: amount(row[1])}


WATCHERS = {
    "wcb_ns_maximum": Watcher(
        "WCB Nova Scotia - Maximum assessable earnings",
        lambda year: (
            "https://www.wcb.ns.ca/employers/workplace-injury-insurance/"
            "rates-and-premiums/maximum-assessable"
        ),
        wcb_ns_maximum,
    ),
}
