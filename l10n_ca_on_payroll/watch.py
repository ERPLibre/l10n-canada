# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watchers of the Ontario pages (see l10n_ca_payroll/tools/watch.py).

The WSIB publishes one page of premium rates per year, which holds the
maximum insurable earnings; the page of a year that is not out answers
404. The EHT page gives the rates and the exemption in force, for every
year until they change.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    find_table,
    normalize,
    rate,
)


def wsib_maximum(content, year):
    text = normalize(document(content).text_content())
    pattern = r"maximum insurable earnings ceiling for (\d{4}) is \$([\d,]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        raise PageChanged("no maximum insurable earnings sentence")
    if int(match.group(1)) != year:
        return None
    return {"l10n_ca.on.wsib.max_insurable": amount(match.group(2))}


def ontario_eht(content, year):
    rows = find_table(content, header=r"Total Ontario remuneration")
    brackets = []
    for row in rows:
        if len(row) < 2 or not row[1].endswith("%"):
            continue
        if row[0].startswith("Up to"):
            lower = 0.0
        else:
            match = re.match(r"(?:Over\s+)?\$([\d,.]+)", row[0])
            if not match:
                raise PageChanged(f"unexpected EHT row {row!r}")
            lower = round(amount(match.group(1)) - (0.01 if "to" in row[0] else 0), 2)
        brackets.append([lower, rate(row[1])])
    if len(brackets) < 2:
        raise PageChanged("no EHT rate table")
    text = normalize(document(content).text_content())
    match = re.search(r"exemption amount is currently \$ ?([\d.,]+) million", text)
    if not match:
        raise PageChanged("no EHT exemption sentence")
    return {
        "l10n_ca.on.eht.rates": brackets,
        "l10n_ca.on.eht.exemption": amount(match.group(1)) * 1_000_000,
    }


WATCHERS = {
    "wsib_rates": Watcher(
        "WSIB - Premium rates and maximum insurable earnings of the year",
        lambda year: f"https://www.wsib.ca/en/{year}premiumrates",
        wsib_maximum,
        "yearly",
    ),
    "ontario_eht": Watcher(
        "Ontario - Employer Health Tax rates and exemption",
        lambda year: "https://www.ontario.ca/document/employer-health-tax-eht",
        ontario_eht,
    ),
}
