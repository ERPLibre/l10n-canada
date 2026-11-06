# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_neq = fields.Char(related="company_id.l10n_ca_neq", readonly=False)
    l10n_ca_ccpc = fields.Boolean(related="company_id.l10n_ca_ccpc", readonly=False)
    l10n_ca_gst_filing_frequency = fields.Selection(
        related="company_id.l10n_ca_gst_filing_frequency", readonly=False
    )
    l10n_ca_qst_filing_frequency = fields.Selection(
        related="company_id.l10n_ca_qst_filing_frequency", readonly=False
    )
    l10n_ca_quick_method = fields.Boolean(
        related="company_id.l10n_ca_quick_method", readonly=False
    )
    l10n_ca_quick_method_date = fields.Date(
        related="company_id.l10n_ca_quick_method_date", readonly=False
    )
    l10n_ca_quick_method_activity = fields.Selection(
        related="company_id.l10n_ca_quick_method_activity", readonly=False
    )
    l10n_ca_instalment_frequency = fields.Selection(
        related="company_id.l10n_ca_instalment_frequency", readonly=False
    )
    l10n_ca_payroll_remitter_type = fields.Selection(
        related="company_id.l10n_ca_payroll_remitter_type", readonly=False
    )
    l10n_ca_qc_remitter_type = fields.Selection(
        related="company_id.l10n_ca_qc_remitter_type", readonly=False
    )
