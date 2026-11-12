# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the Yukon pages (see l10n_ca_payroll/tools/watch.py).

The WSCB page of the maximum annual earnings states the amount of the next
year in one sentence once the Board sets it, in September, and lists the
earlier years as "2026 - $107,599" lines, the current year included.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    normalize,
)

NEXT_YEAR = re.compile(
    r"maximum annual earnings for (\d{4}) (?:will be|is) \$([\d,]+)", re.IGNORECASE
)
PAST_YEAR = re.compile(r"(?<!\d)(\d{4}) [-–—] \$([\d,]+)")


def wscb_maximum(content, year):
    """Return the maximum annual earnings of ``year``, or None if absent.

    The sentence of the next year and the list of the earlier years are
    both read; a page with neither has changed. The texts of the elements
    are joined with a space: the list items of the page follow each other
    without one.
    """
    text = normalize(" ".join(document(content).itertext()))
    years = {int(y): value for y, value in PAST_YEAR.findall(text)}
    years.update({int(y): value for y, value in NEXT_YEAR.findall(text)})
    if not years:
        raise PageChanged("no maximum annual earnings by year")
    if year not in years:
        return None
    return {"l10n_ca.yt.wcb.max_insurable": amount(years[year])}


WATCHERS = {
    "wscb_maximum": Watcher(
        "WSCB - Maximum annual earnings",
        lambda year: "https://www.wcb.yk.ca/web-0021/web-0022/web-0029/web-0030",
        wscb_maximum,
    ),
}
