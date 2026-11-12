# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Read the payroll figures of a year from the official pages.

A watcher is a ``Watcher(label, url, extract, kind)``: ``url(year)`` gives
the address to read, ``extract(content, year)`` returns ``{parameter code:
value}`` for ``year``, or ``None`` while the page does not show that year
yet. A page whose structure no longer matches raises ``PageChanged``: the
caller reports it as a change of the page, never as a missing year. A
watcher of kind ``probe`` only tells whether a document exists: its
``extract`` receives the HTTP status instead of the content. A watcher of
kind ``yearly`` reads a page whose address holds the year: until that page
exists (HTTP 404 or 410), the year is not yet published.

Values follow the storage format of the time parameters: amounts as
numbers, rates as decimals, brackets as ``[[threshold, rate], ...]`` without
the first bracket, which the pages do not give.
"""

import re
from collections import namedtuple

from lxml import etree, html

Watcher = namedtuple("Watcher", "label url extract kind", defaults=("html",))

YEAR_ROW = re.compile(r"^(?:New\s+)?(\d{4})$")


class PageChanged(Exception):
    """The page no longer has the structure the watcher reads."""


def normalize(text):
    """Return ``text`` with every run of spaces, including no-break, as one."""
    return re.sub(r"[\s  ]+", " ", text or "").strip()


def amount(text, decimal_comma=False):
    """Return the number written in ``text`` ("$76,700", "106 000 $")."""
    value = re.sub(r"[\s  $%]", "", text or "")
    value = value.replace(",", ".") if decimal_comma else value.replace(",", "")
    try:
        return float(value)
    except ValueError as error:
        raise PageChanged(f"not a number: {text!r}") from error


def rate(text, decimal_comma=False):
    """Return the decimal rate of a percentage ("5.75", "0,430 %")."""
    return round(amount(text, decimal_comma) / 100, 6)


def document(content):
    """Return the parsed HTML page; bytes are read as UTF-8.

    The official pages are UTF-8; without a declared charset, lxml would
    read the bytes as Latin-1 and lose the accented captions.
    """
    try:
        if isinstance(content, bytes):
            return html.fromstring(content, parser=html.HTMLParser(encoding="utf-8"))
        return html.fromstring(content)
    except (ValueError, TypeError, etree.ParserError) as error:
        raise PageChanged("not an HTML page") from error


def tables(content):
    """Return the tables of an HTML page as (caption, rows of cell texts)."""
    doc = document(content)
    result = []
    for table in doc.iter("table"):
        caption = table.find(".//caption")
        rows = [
            [normalize(cell.text_content()) for cell in row.iter("th", "td")]
            for row in table.iter("tr")
        ]
        result.append(
            (normalize(caption.text_content()) if caption is not None else "", rows)
        )
    return result


def find_table(content, caption_pattern=None, header=None):
    """Return the rows of the first table whose caption matches.

    For a table without caption, ``header`` (a regular expression) is
    matched against the text of its first two rows instead.
    """
    for caption, rows in tables(content):
        found = caption_pattern and re.search(caption_pattern, caption, re.IGNORECASE)
        if caption and found:
            return rows
        first = " ".join(" ".join(row) for row in rows[:2])
        if header and re.search(header, first, re.IGNORECASE):
            return rows
    raise PageChanged(f"no table {caption_pattern or header!r}")


def year_row(rows, year):
    """Return the row whose first cell is ``year`` (or "New year"), or None."""
    years = {}
    for row in rows:
        match = row and YEAR_ROW.match(row[0])
        if match:
            years[int(match.group(1))] = row
    if not years:
        raise PageChanged("no row by year")
    return years.get(year)


def _cells(row, count):
    if len(row) < count:
        raise PageChanged(f"row with {len(row)} cells: {row!r}")
    return row


def cra_cpp(content, year):
    rows = find_table(
        content, r"CPP contribution rates, maximums and exemptions all years"
    )
    row = year_row(rows, year)
    if row is None:
        return None
    row = _cells(row, 5)
    return {
        "l10n_ca.cpp.ympe": amount(row[1]),
        "l10n_ca.cpp.basic_exemption": amount(row[2]),
        "l10n_ca.cpp.rate": rate(row[4]),
    }


def cra_cpp2(content, year):
    rows = find_table(content, r"CPP2 contribution rates and maximums")
    row = year_row(rows, year)
    if row is None:
        return None
    row = _cells(row, 3)
    return {"l10n_ca.cpp.yampe": amount(row[1]), "l10n_ca.cpp.rate2": rate(row[2])}


def cra_ei(content, year):
    federal = year_row(find_table(content, r"^Federal EI premium rates"), year)
    quebec = year_row(find_table(content, r"^Quebec EI premium rates"), year)
    if federal is None or quebec is None:
        return None
    federal, quebec = _cells(federal, 3), _cells(quebec, 3)
    return {
        "l10n_ca.ei.mie": amount(federal[1]),
        "l10n_ca.ei.rate": rate(federal[2]),
        "l10n_ca.ei.rate_qc": rate(quebec[2]),
    }


def _year_column(rows, year):
    header = rows[0] if rows else []
    if not header or header[0] != "Description":
        raise PageChanged(f"unexpected header {header!r}")
    try:
        return header.index(str(year))
    except ValueError:
        return None


def _labelled(rows, column, pattern):
    for row in rows[1:]:
        if row and re.match(pattern, row[0]) and len(row) > column:
            return amount(row[column])
    raise PageChanged(f"no row {pattern!r}")


def cra_indexation(content, year):
    brackets = find_table(content, r"^Tax bracket thresholds")
    credits = find_table(content, r"^Amounts relating to non-refundable tax credits")
    column = _year_column(brackets, year)
    if _year_column(credits, year) != column:
        raise PageChanged(f"{year} is not in the same column of both tables")
    if column is None:
        return None
    thresholds = []
    for row in brackets[1:]:
        match = row and re.match(
            r"Taxable income above which the ([\d.]+)% bracket", row[0]
        )
        if match:
            thresholds.append(
                [amount(row[column]), round(float(match.group(1)) / 100, 6)]
            )
    if len(thresholds) != 4:
        raise PageChanged(f"{len(thresholds)} bracket thresholds instead of 4")
    return {
        "l10n_ca.federal.brackets": thresholds,
        "l10n_ca.federal.bpa_max": _labelled(
            credits, column, r"Basic personal amount \(maximum\)"
        ),
        "l10n_ca.federal.bpa_min": _labelled(
            credits, column, r"Basic personal amount for individuals whose net income"
        ),
        "l10n_ca.federal.bpa_phaseout_start": thresholds[2][0],
        "l10n_ca.federal.bpa_phaseout_end": thresholds[3][0],
        "l10n_ca.federal.canada_employment_amount": _labelled(
            credits, column, r"Canada employment amount"
        ),
    }


def cra_t4127(content, year):
    """Return {} once the edition effective January 1 of ``year`` is listed."""
    text = normalize(document(content).text_content())
    editions = re.findall(r"Edition - Effective (?:January|July) 1, (\d{4})", text)
    if not editions:
        raise PageChanged("no edition listed")
    return {} if f"Effective January 1, {year}" in text else None


def published_document(status, year):
    """Probe: {} when the document answers 200, None for 404 or 410."""
    if status == 200:
        return {}
    if status in (404, 410):
        return None
    raise PageChanged(f"HTTP {status}")


WATCHERS = {
    "cra_cpp": Watcher(
        "CRA - CPP contribution rates, maximums and exemptions",
        lambda year: (
            "https://www.canada.ca/en/revenue-agency/services/tax/"
            "businesses/topics/payroll/payroll-deductions-contributions/"
            "canada-pension-plan-cpp/cpp-contribution-rates-maximums-exemptions.html"
        ),
        cra_cpp,
    ),
    "cra_cpp2": Watcher(
        "CRA - Second additional CPP contribution rates and maximums",
        lambda year: (
            "https://www.canada.ca/en/revenue-agency/services/tax/"
            "businesses/topics/payroll/calculating-deductions/making-deductions/"
            "second-additional-cpp-contribution-rates-maximums.html"
        ),
        cra_cpp2,
    ),
    "cra_ei": Watcher(
        "CRA - EI premium rates and maximums",
        lambda year: (
            "https://www.canada.ca/en/revenue-agency/services/tax/"
            "businesses/topics/payroll/payroll-deductions-contributions/"
            "employment-insurance-ei/ei-premium-rates-maximums.html"
        ),
        cra_ei,
    ),
    "cra_indexation": Watcher(
        "CRA - Indexation of personal income tax and benefit amounts",
        lambda year: (
            "https://www.canada.ca/en/revenue-agency/services/tax/"
            "individuals/frequently-asked-questions-individuals/"
            "adjustment-personal-income-tax-benefit-amounts.html"
        ),
        cra_indexation,
    ),
    "cra_t4127": Watcher(
        "CRA - T4127 Payroll Deductions Formulas, January edition",
        lambda year: (
            "https://www.canada.ca/en/revenue-agency/services/"
            "forms-publications/payroll/t4127-payroll-deductions-formulas.html"
        ),
        cra_t4127,
    ),
}
