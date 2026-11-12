# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Manitoba on the common provincial engine of l10n_ca_payroll.

The engine computes the Manitoba income tax (T4127 option 1, steps 4 to 6,
with the labour-sponsored funds credit LCP), the Health and Post Secondary
Education Tax Levy and the WCB Manitoba premium from the parameters
``l10n_ca.mb.*``. Manitoba adds to it the income-tested basic personal
amount BPAMB.
"""

from odoo import _, api, models
from odoo.tools import float_round

_PREFIX = "l10n_ca.mb"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "MB": _PREFIX}

    @api.model
    def _l10n_ca_employer_tax_name(self, province):
        if province.code == "MB":
            return _("Health and Post Secondary Education Tax Levy")
        return super()._l10n_ca_employer_tax_name(province)

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "MB":
            return _("WCB Manitoba Premium")
        return super()._l10n_ca_wcb_name(province)

    def _l10n_ca_prov_bpa(self, vals, prefix, income):
        """Return BPAMB, the Manitoba basic personal amount of the annual
        income ``income`` (NI of T4127).

        The maximum ``l10n_ca.mb.bpa`` up to ``l10n_ca.mb.bpa_phaseout_start``,
        0 from ``l10n_ca.mb.bpa_phaseout_end``, and in between the maximum
        less (NI - start) x (maximum / (end - start)), the division not
        rounded and the result rounded half up to the cent.
        """
        maximum = super()._l10n_ca_prov_bpa(vals, prefix, income)
        if prefix != _PREFIX:
            return maximum
        start = self._l10n_ca_prov_param(vals, prefix, "bpa_phaseout_start")
        end = self._l10n_ca_prov_param(vals, prefix, "bpa_phaseout_end")
        if income <= start:
            return maximum
        if income >= end:
            return 0.0
        return float_round(
            maximum - (income - start) * (maximum / (end - start)),
            precision_digits=2,
        )
