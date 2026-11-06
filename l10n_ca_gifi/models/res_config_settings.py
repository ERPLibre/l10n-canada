# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ca_gifi_closing_journal_ids = fields.Many2many(
        related="company_id.l10n_ca_gifi_closing_journal_ids", readonly=False
    )
