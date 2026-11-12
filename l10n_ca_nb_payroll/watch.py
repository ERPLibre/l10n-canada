# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the New Brunswick pages (see l10n_ca_payroll/tools/watch.py).

WorkSafeNB policy 37-110 states the maximum assessable earnings of the
year in force in one sentence; it is updated near January 1, so the next
year stays "not yet published" there until then.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    normalize,
)


def worksafenb_maximum(content, year):
    text = normalize(document(content).text_content())
    match = re.search(
        r"The (\d{4}) yearly maximum assessable earnings is [^(]*\(\$([\d,]+)\)",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise PageChanged("no yearly maximum assessable earnings sentence")
    if int(match.group(1)) != year:
        return None
    return {"l10n_ca.nb.wcb.max_insurable": amount(match.group(2))}


WATCHERS = {
    "worksafenb_maximum": Watcher(
        "WorkSafeNB - Maximum assessable earnings of the year (policy 37-110)",
        lambda year: (
            "https://www.worksafenb.ca/policy-and-legal/policy/view-our-policies/"
            "new-brunswick-industrial-aggregate-earnings"
        ),
        worksafenb_maximum,
    ),
}
