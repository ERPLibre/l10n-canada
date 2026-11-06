# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_dividend_account_id = fields.Many2one(
        related="company_id.l10n_ca_dividend_account_id", readonly=False
    )
    l10n_ca_dividend_payable_account_id = fields.Many2one(
        related="company_id.l10n_ca_dividend_payable_account_id", readonly=False
    )
    l10n_ca_dividend_journal_id = fields.Many2one(
        related="company_id.l10n_ca_dividend_journal_id", readonly=False
    )
    l10n_ca_grip_balance = fields.Monetary(
        related="company_id.l10n_ca_grip_balance", readonly=False
    )
    l10n_ca_grip_date = fields.Date(
        related="company_id.l10n_ca_grip_date", readonly=False
    )
    l10n_ca_shareholder_loan_reminder_days = fields.Integer(
        related="company_id.l10n_ca_shareholder_loan_reminder_days", readonly=False
    )
    l10n_ca_corporate_tax_user_id = fields.Many2one(
        related="company_id.l10n_ca_corporate_tax_user_id", readonly=False
    )
    l10n_ca_qc_instalment_frequency = fields.Selection(
        related="company_id.l10n_ca_qc_instalment_frequency", readonly=False
    )
