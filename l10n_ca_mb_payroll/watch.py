# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the Manitoba pages (see l10n_ca_payroll/tools/watch.py).

The WCB Manitoba assessable payroll fact sheet states the maximum
assessable earnings of each year it covers in one sentence ("In 2025,
the maximum level of assessable earnings is $167,050." / "For 2026, ...").
A year without its sentence is not yet published there.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    normalize,
)

_MAXIMUM_SENTENCE = re.compile(
    r"(?:In|For) (\d{4}), the maximum level of assessable earnings is "
    r"\$([\d,]+)",
    re.IGNORECASE,
)


def wcb_mb_maximum(content, year):
    """Return the maximum assessable earnings of ``year`` from the fact
    sheet, None when the page has no sentence for ``year``.

    Raises PageChanged when the page has no such sentence at all.
    """
    text = normalize(document(content).text_content())
    found = {
        int(match.group(1)): match.group(2)
        for match in _MAXIMUM_SENTENCE.finditer(text)
    }
    if not found:
        raise PageChanged("no maximum level of assessable earnings sentence")
    if year not in found:
        return None
    return {"l10n_ca.mb.wcb.max_insurable": amount(found[year])}


WATCHERS = {
    "wcb_mb_maximum": Watcher(
        "WCB Manitoba - Maximum assessable earnings of the year (fact sheet)",
        lambda year: "https://www.wcb.mb.ca/assessable-payroll-fact-sheet/",
        wcb_mb_maximum,
    ),
}
