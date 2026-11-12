# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_qc_rq_account_number = fields.Char(
        related="company_id.l10n_ca_qc_rq_account_number", readonly=False
    )
    l10n_ca_qc_hsf_sector = fields.Selection(
        related="company_id.l10n_ca_qc_hsf_sector", readonly=False
    )
    l10n_ca_qc_hsf_basis = fields.Selection(
        related="company_id.l10n_ca_qc_hsf_basis", readonly=False
    )
    l10n_ca_qc_total_payroll_estimate = fields.Monetary(
        related="company_id.l10n_ca_qc_total_payroll_estimate", readonly=False
    )
    l10n_ca_qc_wsdrf_payroll_estimate = fields.Monetary(
        related="company_id.l10n_ca_qc_wsdrf_payroll_estimate", readonly=False
    )
    l10n_ca_qc_associated_payroll = fields.Monetary(
        related="company_id.l10n_ca_qc_associated_payroll", readonly=False
    )
    l10n_ca_qc_cnesst_rate = fields.Float(
        related="company_id.l10n_ca_qc_cnesst_rate", readonly=False
    )
    l10n_ca_qc_cnt_exempt = fields.Boolean(
        related="company_id.l10n_ca_qc_cnt_exempt", readonly=False
    )
    l10n_ca_qc_lump_sum_method = fields.Selection(
        related="company_id.l10n_ca_qc_lump_sum_method", readonly=False
    )
