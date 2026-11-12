# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Saskatchewan on the common provincial engine of l10n_ca_payroll.

The engine computes the Saskatchewan income tax (T4127 option 1, steps 4
to 6, with the labour-sponsored funds credit LCP) and the Saskatchewan
Workers' Compensation Board premium from the parameters
``l10n_ca.sk.*``. Saskatchewan has no factor of its own besides LCP and
no employer payroll tax.
"""

from odoo import _, api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "SK": "l10n_ca.sk"}

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "SK":
            return _("Saskatchewan WCB Premium")
        return super()._l10n_ca_wcb_name(province)
