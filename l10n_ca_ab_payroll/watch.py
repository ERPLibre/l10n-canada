# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Watcher of the WCB-Alberta fact sheet (see l10n_ca_payroll/tools/watch.py).

The fact sheet WCB-615 "Maximum Compensable and Assessable Earnings" is a
PDF at a fixed address. It states the maximum assessable earnings (MAE)
of the years it covers in sentences "in YYYY, the MAE is $NNN,NNN"; it is
reissued near January 1, so the next year stays "not yet published" there
until then.
"""

import io
import re

from odoo.tools.pdf import PdfReader

from odoo.addons.l10n_ca_payroll.tools.watch import (
    PageChanged,
    Watcher,
    amount,
    normalize,
)

MAE_SENTENCE = re.compile(r"in (\d{4}),? the MAE is \$ ?([\d,]+)", re.IGNORECASE)


def pdf_text(content):
    """Return the text of the PDF ``content`` (bytes), spaces normalized.

    Raises ``PageChanged`` when ``content`` is not a readable PDF.
    """
    if not content or not content.startswith(b"%PDF"):
        raise PageChanged("not a PDF document")
    try:
        reader = PdfReader(io.BytesIO(content))
        return normalize(" ".join(page.extract_text() or "" for page in reader.pages))
    except Exception as error:
        raise PageChanged(f"unreadable PDF ({error!r})") from error


def wcb_alberta_maximum(content, year):
    """Return the MAE of ``year`` stated by the fact sheet, or None.

    Raises ``PageChanged`` when the fact sheet states no MAE at all.
    """
    found = {int(y): value for y, value in MAE_SENTENCE.findall(pdf_text(content))}
    if not found:
        raise PageChanged("no maximum assessable earnings sentence")
    if year not in found:
        return None
    return {"l10n_ca.ab.wcb.max_insurable": amount(found[year])}


WATCHERS = {
    "wcb_alberta_maximum": Watcher(
        "WCB-Alberta - Maximum assessable earnings of the year (fact sheet WCB-615)",
        lambda year: (
            "https://www.wcb.ab.ca/assets/pdfs/employers/"
            "EFS_Maximum_compensable_and_assessable_earnings.pdf"
        ),
        wcb_alberta_maximum,
    ),
}
