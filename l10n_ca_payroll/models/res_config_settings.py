# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_payroll_account_number = fields.Char(
        related="company_id.l10n_ca_payroll_account_number", readonly=False
    )
    l10n_ca_ei_employer_multiplier = fields.Float(
        related="company_id.l10n_ca_ei_employer_multiplier", readonly=False
    )

    def action_l10n_ca_payroll_setup(self):
        self.ensure_one()
        self.company_id.l10n_ca_payroll_setup()
        return True
