# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_ca_shareholder_loan = fields.Boolean(
        string="Shareholder Loan",
        help="Debit balances of this account per partner are amounts lent to a "
        "shareholder or a connected person: the shareholder loan follow-up "
        "(ITA s. 15(2), 80.4) reads its journal items.",
    )
    l10n_ca_tax_treatment = fields.Selection(
        [
            ("meals", "Meals and entertainment (partially deductible)"),
            ("non_deductible", "Non-deductible expense"),
            ("investment", "Investment income"),
        ],
        string="Corporate Tax Treatment",
        help="Used by the corporate tax estimate: meals and entertainment "
        "are added back for their non-deductible portion, non-deductible "
        "expenses (fines, income tax expense, ...) are added back in full, "
        "and investment income is proposed as aggregate investment income.",
    )
