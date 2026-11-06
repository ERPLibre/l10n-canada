# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_gst_authority_account_id = fields.Many2one(
        related="company_id.l10n_ca_gst_authority_account_id", readonly=False
    )
    l10n_ca_qst_authority_account_id = fields.Many2one(
        related="company_id.l10n_ca_qst_authority_account_id", readonly=False
    )
    l10n_ca_tax_closing_journal_id = fields.Many2one(
        related="company_id.l10n_ca_tax_closing_journal_id", readonly=False
    )
    l10n_ca_quick_method_gain_account_id = fields.Many2one(
        related="company_id.l10n_ca_quick_method_gain_account_id", readonly=False
    )
    l10n_ca_bad_debt_account_id = fields.Many2one(
        related="company_id.l10n_ca_bad_debt_account_id", readonly=False
    )
    l10n_ca_bad_debt_recovery_account_id = fields.Many2one(
        related="company_id.l10n_ca_bad_debt_recovery_account_id", readonly=False
    )
