# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the British Columbia pages (see l10n_ca_payroll/tools/watch.py).

The WorkSafeBC page of the maximum wage rates states the rate of the next
year in one sentence ("The maximum wage rate for YYYY, effective ..., is
$N.") and each earlier year in another ("... set the YYYY Maximum Wage Rate
amount at $N"). WorkSafeBC assesses the payroll of each worker up to that
rate, the maximum assessable earnings of the year.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    normalize,
)

_AMOUNT = r"\$([\d,]+(?:\.\d{2})?)"
_SENTENCES = (
    re.compile(
        r"maximum wage rate for (\d{4}), effective [^,]+, \d{4}, is " + _AMOUNT,
        re.IGNORECASE,
    ),
    re.compile(
        r"set the (\d{4}) maximum wage rate amount at " + _AMOUNT, re.IGNORECASE
    ),
)


def worksafebc_maximum(content, year):
    """Return the maximum assessable earnings of ``year``, or None.

    Raises ``PageChanged`` when the page states no maximum wage rate at all.
    """
    text = normalize(document(content).text_content())
    rates = {}
    for sentence in _SENTENCES:
        for match in sentence.finditer(text):
            rates.setdefault(int(match.group(1)), amount(match.group(2)))
    if not rates:
        raise PageChanged("no maximum wage rate sentence")
    if year not in rates:
        return None
    return {"l10n_ca.bc.wcb.max_insurable": rates[year]}


WATCHERS = {
    "worksafebc_maximum": Watcher(
        "WorkSafeBC - Maximum wage rate (maximum assessable earnings) of the year",
        lambda year: (
            "https://www.worksafebc.com/en/law-policy/claims-rehabilitation/"
            "compensation-related-maximum-wage-rates"
        ),
        worksafebc_maximum,
    ),
}
