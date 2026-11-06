# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_gst_prior_net_tax = fields.Monetary(
        related="company_id.l10n_ca_gst_prior_net_tax", readonly=False
    )
    l10n_ca_qst_prior_net_tax = fields.Monetary(
        related="company_id.l10n_ca_qst_prior_net_tax", readonly=False
    )
    l10n_ca_files_t5 = fields.Boolean(
        related="company_id.l10n_ca_files_t5", readonly=False
    )
    l10n_ca_req_combined_with_co17 = fields.Boolean(
        related="company_id.l10n_ca_req_combined_with_co17", readonly=False
    )
    l10n_ca_tax_deadline_user_id = fields.Many2one(
        related="company_id.l10n_ca_tax_deadline_user_id", readonly=False
    )
    l10n_ca_tax_deadline_reminder_days = fields.Integer(
        related="company_id.l10n_ca_tax_deadline_reminder_days", readonly=False
    )
    l10n_ca_tax_deadline_horizon_months = fields.Integer(
        related="company_id.l10n_ca_tax_deadline_horizon_months", readonly=False
    )
    l10n_ca_qc_instalment_frequency = fields.Selection(
        related="company_id.l10n_ca_qc_instalment_frequency", readonly=False
    )
