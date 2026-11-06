# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_gst_authority_account_id = fields.Many2one(
        "account.account",
        string="GST/HST Return Account",
        check_company=True,
        help="Receives the net tax of the GST/HST (GST34) returns when they "
        "are closed: the account of the Canada Revenue Agency.",
    )
    l10n_ca_qst_authority_account_id = fields.Many2one(
        "account.account",
        string="Revenu Quebec Account",
        check_company=True,
        help="Receives the net GST/HST and QST of the Quebec (FPZ-500) "
        "returns when they are closed. A Quebec registrant files both taxes "
        "with Revenu Quebec.",
    )
    l10n_ca_tax_closing_journal_id = fields.Many2one(
        "account.journal",
        string="Sales Tax Closing Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
        help="Journal of the closing entries and of the bad debt "
        "adjustments. The first miscellaneous journal when empty.",
    )
    l10n_ca_quick_method_gain_account_id = fields.Many2one(
        "account.account",
        string="Quick Method Gain Account",
        check_company=True,
        help="Receives the difference between the tax recorded in the books "
        "and the tax remitted under the quick method.",
    )
    l10n_ca_bad_debt_account_id = fields.Many2one(
        "account.account",
        string="Bad Debt Expense Account",
        check_company=True,
    )
    l10n_ca_bad_debt_recovery_account_id = fields.Many2one(
        "account.account",
        string="Bad Debt Recovery Account",
        check_company=True,
        help="Income account of a recovered bad debt. The bad debt expense "
        "account when empty.",
    )

    def _l10n_ca_tax_closing_journal(self):
        self.ensure_one()
        return self.l10n_ca_tax_closing_journal_id or self.env[
            "account.journal"
        ].search(
            [
                *self.env["account.journal"]._check_company_domain(self),
                ("type", "=", "general"),
            ],
            limit=1,
        )
