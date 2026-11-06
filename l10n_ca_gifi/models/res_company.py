# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

# GIFI codes of the accounts that the chart loader creates outside the
# template (account.chart.template._setup_utility_bank_accounts): the
# company field, or the xmlid suffix, that designates each of them.
_UTILITY_ACCOUNT_CODES = {
    "account_journal_suspense_account_id": "1002",
    "transfer_account_id": "1002",
    "default_cash_difference_income_account_id": "8230",
    "default_cash_difference_expense_account_id": "9270",
}
_UTILITY_XMLID_CODES = {
    "account_journal_payment_debit_account_id": "1002",
    "account_journal_payment_credit_account_id": "1002",
}
_JOURNAL_TYPE_CODES = {"bank": "1002", "cash": "1001", "credit": "2707"}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_gifi_closing_journal_ids = fields.Many2many(
        "account.journal",
        "l10n_ca_gifi_closing_journal_rel",
        "company_id",
        "journal_id",
        string="GIFI Closing Journals",
        help="Entries of these journals (year-end closing and reopening) "
        "are ignored by the GIFI statement, which reports the balances "
        "before closing.",
    )

    def _l10n_ca_gifi_code(self, code):
        return self.env.ref(f"l10n_ca_gifi.gifi_{code}", raise_if_not_found=False)

    def _l10n_ca_gifi_assign_default_codes(self):
        """Set the GIFI code of the ca_2023 accounts that have none.

        Covers the template accounts, the utility accounts created by the
        chart loader and the default accounts of the bank, cash and credit
        card journals. An account that already has a code keeps it.
        """
        ChartTemplate = self.env["account.chart.template"]
        template_codes = ChartTemplate._parse_csv(
            "ca_2023", "account.account", module="l10n_ca_gifi"
        )
        for company in self.filtered(lambda c: c.chart_template == "ca_2023"):
            chart = ChartTemplate.with_company(company)
            assignments = []
            for xmlid, values in template_codes.items():
                account = chart.ref(xmlid, raise_if_not_found=False)
                code = self.env.ref(values["l10n_ca_gifi_code_id"])
                assignments.append((account, code))
            for field, code in _UTILITY_ACCOUNT_CODES.items():
                assignments.append((company[field], company._l10n_ca_gifi_code(code)))
            for suffix, code in _UTILITY_XMLID_CODES.items():
                account = self.env.ref(
                    f"account.{company.id}_{suffix}", raise_if_not_found=False
                )
                assignments.append((account, company._l10n_ca_gifi_code(code)))
            journals = self.env["account.journal"].search(
                [
                    ("company_id", "=", company.id),
                    ("type", "in", list(_JOURNAL_TYPE_CODES)),
                ]
            )
            for journal in journals:
                code = company._l10n_ca_gifi_code(_JOURNAL_TYPE_CODES[journal.type])
                assignments.append((journal.default_account_id, code))
            for account, code in assignments:
                if account and code and not account.l10n_ca_gifi_code_id:
                    account.l10n_ca_gifi_code_id = code
