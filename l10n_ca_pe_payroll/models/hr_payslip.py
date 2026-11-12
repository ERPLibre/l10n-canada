# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Prince Edward Island on the common provincial engine of l10n_ca_payroll.

The engine computes the Prince Edward Island income tax (T4127 option 1,
steps 4 to 6) and the WCB PEI assessment from the parameters
``l10n_ca.pe.*``. Prince Edward Island has no factor of its own (no
surtax, premium, reduction or labour-sponsored funds credit) and no
employer payroll tax: the rate of the bracket above 200,000, prorated on
July 1, 2026, is a dated version of ``l10n_ca.pe.brackets``.
"""

from odoo import _, api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "PE": "l10n_ca.pe"}

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "PE":
            return _("WCB PEI Assessment")
        return super()._l10n_ca_wcb_name(province)
