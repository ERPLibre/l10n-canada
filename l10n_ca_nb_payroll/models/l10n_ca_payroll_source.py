# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models

from ..watch import WATCHERS


class L10nCaPayrollSource(models.Model):
    _inherit = "l10n_ca.payroll.source"

    @api.model
    def _l10n_ca_watchers(self):
        """Add the watchers of the New Brunswick pages."""
        watchers = super()._l10n_ca_watchers()
        watchers.update(WATCHERS)
        return watchers
