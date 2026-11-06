# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo.fields import Command
from odoo.tools.translate import TranslationImporter, get_po_paths

from .models.account_chart_template import LINE_101_TAXES

_logger = logging.getLogger(__name__)

COMPANY_DEFAULT_ACCOUNTS = {
    "l10n_ca_gst_authority_account_id": "l10n_ca_221210",
    "l10n_ca_qst_authority_account_id": "l10n_ca_221210",
    "l10n_ca_quick_method_gain_account_id": "l10n_ca_413300",
}

# FPZ-500 report lines of l10n_ca whose names i18n/fr.po of this module
# translates, in place of the l10n_ca translations.
REPORT_LINE_TERMS = frozenset(
    f"l10n_ca.l10n_ca_tr_qst_{line}"
    for line in ("101", "103_203", "106_206", "108_208", "111_211")
)

LOCK_DATE_FIELDS = (
    "fiscalyear_lock_date",
    "tax_lock_date",
    "sale_lock_date",
    "purchase_lock_date",
    "hard_lock_date",
)


def _line_101_tags(env):
    country = env.ref("base.ca")
    tags = env["account.account.tag"]._get_tax_tags("CaQc101", country.id)
    return (
        tags.filtered(lambda t: not t.tax_negate),
        tags.filtered(lambda t: t.tax_negate),
    )


def l10n_ca_tag_line_101(env, companies):
    """Add the FPZ-500 line 101 tag to the 0% international and exempt taxes.

    Applies to the companies on the ca_2023 chart, on the taxes and on the
    base journal items dated after the tax lock date and not hashed, which
    the returns of open periods read. Line 101 is informational, so
    retagging posted items does not change any tax amount. Returns the
    number of retagged items.
    """
    plus_tag, minus_tag = _line_101_tags(env)
    if not plus_tag or not minus_tag:
        return 0
    count = 0
    for company in companies.filtered(lambda c: c.chart_template == "ca_2023"):
        chart = env["account.chart.template"].with_company(company)
        taxes = env["account.tax"]
        for xmlid in LINE_101_TAXES:
            taxes |= chart.ref(xmlid, raise_if_not_found=False) or taxes
        for tax in taxes:
            for line in tax.repartition_line_ids.filtered(
                lambda rl: rl.repartition_type == "base"
            ):
                tag = plus_tag if line.document_type == "invoice" else minus_tag
                if tag not in line.tag_ids:
                    line.tag_ids = [Command.link(tag.id)]
        if not taxes:
            continue
        domain = [
            ("company_id", "=", company.id),
            ("tax_ids", "in", taxes.ids),
            ("tax_line_id", "=", False),
            ("tax_tag_ids", "not in", (plus_tag | minus_tag).ids),
            ("move_id.inalterable_hash", "=", False),
        ]
        # Writing tax tags on a posted item is refused before any lock date
        # of the company or of its parents (fiscal year, tax, sales,
        # purchases, hard lock): items on or before the latest one keep
        # their tags, so the install never hits a lock date error.
        lock_dates = [
            parent[field]
            for parent in company.sudo().parent_ids
            for field in LOCK_DATE_FIELDS
            if parent[field]
        ]
        if lock_dates:
            domain.append(("date", ">", max(lock_dates)))
        lines = env["account.move.line"].search(domain)
        refunds = lines.filtered("is_refund")
        for subset, tag in ((lines - refunds, plus_tag), (refunds, minus_tag)):
            if subset:
                subset.write({"tax_tag_ids": [Command.link(tag.id)]})
        count += len(lines)
    return count


def l10n_ca_load_report_line_terms(env):
    """Load the names of REPORT_LINE_TERMS from the i18n files of this module.

    The terms of a module load without overwriting an existing
    translation, so at install time the names l10n_ca loaded before this
    module stay. These entries alone are loaded again here, for every
    installed language, overwriting them. A language activated later loads
    l10n_ca then this module in one pass, in which the later entry wins.
    """
    importer = TranslationImporter(env.cr, verbose=False)
    for lang, __ in env["res.lang"].get_installed():
        for po_path in get_po_paths("l10n_ca_tax_return", lang):
            importer.load_file(po_path, lang, xmlids=REPORT_LINE_TERMS)
    importer.save(overwrite=True)


def post_init_hook(env):
    companies = env["res.company"].search([("chart_template", "=", "ca_2023")])
    for company in companies:
        chart = env["account.chart.template"].with_company(company)
        for field, xmlid in COMPANY_DEFAULT_ACCOUNTS.items():
            if not company[field]:
                account = chart.ref(xmlid, raise_if_not_found=False)
                if account:
                    company[field] = account
    count = l10n_ca_tag_line_101(env, companies)
    _logger.info("FPZ-500 line 101 tag added to %s journal items", count)
    l10n_ca_load_report_line_terms(env)
