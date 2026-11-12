# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watchers of the Quebec payroll pages (see l10n_ca_payroll/tools/watch.py).

The HTML pages of Revenu Quebec refuse automatic clients: its publications
are watched as PDF documents, which answer 200 once published and 410
before. The QPP, QPIP and CNESST figures are read on the pages of Retraite
Quebec, Quebec.ca and the CNESST, which give each year in a table.
"""

import re

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    document,
    find_table,
    normalize,
    published_document,
    rate,
    tables,
    year_row,
)


def _latest_table(content, pattern):
    """Return the rows of the table whose caption ends with the latest years."""
    best = None
    for caption, rows in tables(content):
        match = re.search(pattern + r".*?(\d{4})\s*-\s*(\d{4})", caption, re.IGNORECASE)
        if match and (best is None or int(match.group(2)) > best[0]):
            best = (int(match.group(2)), rows)
    if best is None:
        raise PageChanged(f"no table {pattern!r}")
    return best[1]


def retraite_quebec_qpp(content, year):
    base = _latest_table(content, r"between the basic exemption and the maximum")
    second = _latest_table(content, r"additional maximum annual pensionable")
    row, row2 = year_row(base, year), year_row(second, year)
    if row is None or row2 is None:
        return None
    if len(row) < 4 or len(row2) < 4:
        raise PageChanged(f"short rows {row!r} {row2!r}")
    return {
        "l10n_ca.qpp.basic_exemption": amount(row[1]),
        "l10n_ca.qpp.ympe": amount(row[2]),
        "l10n_ca.qpp.rate": rate(row[3]),
        "l10n_ca.qpp.yampe": amount(row2[2]),
        "l10n_ca.qpp.rate2": rate(row2[3]),
    }


def quebec_qpip_rates(content, year):
    rows = find_table(content, header=r"Type de cotisants")
    header = next((r for r in rows if r and r[0] == "Type de cotisants"), None)
    if header is None:
        raise PageChanged("no header Type de cotisants")
    if str(year) not in header:
        return None
    column = header.index(str(year))
    values = {}
    for label, code in (
        ("Salariés", "l10n_ca.qpip.rate"),
        ("Employeurs", "l10n_ca.qpip.employer_rate"),
    ):
        row = next((r for r in rows if r and r[0] == label), None)
        match = row and re.search(r"Taux de cotisation\s*:\s*([\d,]+)\s*%", row[column])
        if not match:
            raise PageChanged(f"no rate for {label}")
        values[code] = rate(match.group(1), decimal_comma=True)
    return values


def quebec_qpip_mie(content, year):
    text = normalize(document(content).text_content())
    found = re.findall(r"([\d ]+) \$ pour (\d{4})", text)
    if not found:
        raise PageChanged("no maximum insurable earnings sentence")
    for value, found_year in found:
        if int(found_year) == year:
            return {"l10n_ca.qpip.mie": amount(value, decimal_comma=True)}
    return None


def cnesst_maximum(content, year):
    rows = find_table(
        content, r"Maximum du salaire assurable par année de tarification"
    )
    row = year_row(rows, year)
    if row is None:
        return None
    return {"l10n_ca.qc.cnesst.max_insurable": amount(row[1], decimal_comma=True)}


WATCHERS = {
    "rq_tp1015f": Watcher(
        "Revenu Québec - TP-1015.F, January edition",
        lambda year: (
            "https://www.revenuquebec.ca/documents/fr/formulaires/tp/"
            f"TP-1015.F%28{year}-01%29.pdf"
        ),
        published_document,
        "probe",
    ),
    "rq_tp1015g": Watcher(
        "Revenu Québec - TP-1015.G (main changes), January edition",
        lambda year: (
            "https://www.revenuquebec.ca/documents/fr/formulaires/tp/"
            f"TP-1015.G%28{year}-01%29.pdf"
        ),
        published_document,
        "probe",
    ),
    "finances_qc_indexation": Watcher(
        "Finances Québec - Paramètres du régime d'imposition des particuliers",
        lambda year: (
            "https://cdn-contenu.quebec.ca/cdn-contenu/adm/min/finances/"
            f"publications-adm/parametres/AUTFR_RegimeImpot{year}.pdf"
        ),
        published_document,
        "probe",
    ),
    "retraite_quebec_qpp": Watcher(
        "Retraite Québec - QPP pensionable earnings and contributions",
        lambda year: (
            "https://www.retraitequebec.gouv.qc.ca/en/programs/"
            "quebec-pension-plan/work-contributions/pensionable-earnings-contributions"
        ),
        retraite_quebec_qpp,
    ),
    "quebec_qpip_rates": Watcher(
        "Québec.ca - QPIP premium rates",
        lambda year: (
            "https://www.quebec.ca/entreprises-et-travailleurs-autonomes/"
            "administrer-gerer/embauche-gestion-personnel/assurance-parentale/"
            "taux-cotisations"
        ),
        quebec_qpip_rates,
    ),
    "quebec_qpip_mie": Watcher(
        "Québec.ca - QPIP maximum insurable earnings",
        lambda year: (
            "https://www.quebec.ca/entreprises-et-travailleurs-autonomes/"
            "administrer-gerer/embauche-gestion-personnel/assurance-parentale/"
            "revenu-maximal-assurable"
        ),
        quebec_qpip_mie,
    ),
    "cnesst_maximum": Watcher(
        "CNESST - Maximum annual insurable earnings",
        lambda year: (
            "https://www.cnesst.gouv.qc.ca/fr/demarches-formulaires/"
            "employeurs/assurance-sante-securite-travail/tarification/"
            "annexes-tableaux/salaire-maximum-annuel-assurable"
        ),
        cnesst_maximum,
    ),
}
