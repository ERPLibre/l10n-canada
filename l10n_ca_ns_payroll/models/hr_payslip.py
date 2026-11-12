# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Nova Scotia on the common provincial engine of l10n_ca_payroll.

The engine computes the Nova Scotia income tax (T4127 option 1, steps 4 to
6, with the labour-sponsored funds credit LCP) and the WCB Nova Scotia
premium from the parameters ``l10n_ca.ns.*``. The Nova Scotia basic
personal amount is the same for every income from 2026 (T4127 removes the
income-tested BPANS formula), so the engine's flat ``<prefix>.bpa`` applies.
Nova Scotia has no factor of its own and no employer payroll tax.
"""

from odoo import _, api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "NS": "l10n_ca.ns"}

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "NS":
            return _("WCB Nova Scotia Premium")
        return super()._l10n_ca_wcb_name(province)
