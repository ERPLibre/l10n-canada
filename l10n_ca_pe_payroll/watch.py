# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the Prince Edward Island pages (see l10n_ca_payroll/tools/watch.py).

The WCB PEI page "Rates and Payments" states the maximum assessable
earnings (MAE) of one year in one sentence, "The MAE for <year> is
$<amount>."; the board replaces it with the next year once announced, so
that year stays "not yet published" there until then.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    normalize,
)


def wcb_pei_maximum(content, year):
    text = normalize(document(content).text_content())
    match = re.search(r"The MAE for (\d{4}) is \$([\d,]+)", text, re.IGNORECASE)
    if not match:
        raise PageChanged("no maximum assessable earnings (MAE) sentence")
    if int(match.group(1)) != year:
        return None
    return {"l10n_ca.pe.wcb.max_insurable": amount(match.group(2))}


WATCHERS = {
    "wcb_pei_maximum": Watcher(
        "WCB PEI - Maximum assessable earnings of the year (Rates and Payments)",
        lambda year: "https://www.wcb.pe.ca/rates-and-payments",
        wcb_pei_maximum,
    ),
}
