# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_on_eht_account_number = fields.Char(
        related="company_id.l10n_ca_on_eht_account_number", readonly=False
    )
    l10n_ca_on_eht_eligible = fields.Boolean(
        related="company_id.l10n_ca_on_eht_eligible", readonly=False
    )
    l10n_ca_on_eht_charity = fields.Boolean(
        related="company_id.l10n_ca_on_eht_charity", readonly=False
    )
    l10n_ca_on_eht_associated = fields.Boolean(
        related="company_id.l10n_ca_on_eht_associated", readonly=False
    )
    l10n_ca_on_eht_allocated_exemption = fields.Monetary(
        related="company_id.l10n_ca_on_eht_allocated_exemption", readonly=False
    )
    l10n_ca_on_eht_basis = fields.Selection(
        related="company_id.l10n_ca_on_eht_basis", readonly=False
    )
    l10n_ca_on_eht_previous_payroll = fields.Monetary(
        related="company_id.l10n_ca_on_eht_previous_payroll", readonly=False
    )
    l10n_ca_on_eht_estimated_payroll = fields.Monetary(
        related="company_id.l10n_ca_on_eht_estimated_payroll", readonly=False
    )
    l10n_ca_on_wsib_account_number = fields.Char(
        related="company_id.l10n_ca_on_wsib_account_number", readonly=False
    )
    l10n_ca_on_wsib_rate = fields.Float(
        related="company_id.l10n_ca_on_wsib_rate", readonly=False
    )
