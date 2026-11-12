# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Ontario factors of the common provincial engine of l10n_ca_payroll.

The engine computes the Ontario income tax (T4127 option 1, steps 4 to 6),
the Employer Health Tax and the WSIB premium from the parameters
``l10n_ca.on.*``. Ontario adds to it the surtax (V1), the Ontario Health
Premium (V2), due whatever the claim, and the Ontario tax reduction (S)
with the amount per dependant of factor Y.
"""

from odoo import _, api, models

from ..tools import health_premium, surtax, tax_reduction


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "ON": "l10n_ca.on"}

    @api.model
    def _l10n_ca_prov_rule_codes(self, province):
        if province.code == "ON":
            return {"remuneration": "CA_ON_SAL", "wcb_insurable": "CA_ON_WSIB_IE"}
        return super()._l10n_ca_prov_rule_codes(province)

    @api.model
    def _l10n_ca_employer_tax_name(self, province):
        if province.code == "ON":
            return _("Ontario Employer Health Tax")
        return super()._l10n_ca_employer_tax_name(province)

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "ON":
            return _("WSIB Premium")
        return super()._l10n_ca_wcb_name(province)

    def _l10n_ca_prov_surtax(self, vals, prefix, basic_tax):
        """V1 = 20% of T4 above the first threshold plus 36% of T4 above
        the second (``l10n_ca.on.surtax``)."""
        if prefix != "l10n_ca.on":
            return super()._l10n_ca_prov_surtax(vals, prefix, basic_tax)
        schedule = self._l10n_ca_prov_param(vals, prefix, "surtax")
        return surtax(basic_tax, schedule)

    def _l10n_ca_prov_premium(self, vals, prefix, income):
        """V2, the Ontario Health Premium on A (``l10n_ca.on.health_premium``),
        due even under claim code E."""
        if prefix != "l10n_ca.on":
            return super()._l10n_ca_prov_premium(vals, prefix, income)
        schedule = self._l10n_ca_prov_param(vals, prefix, "health_premium")
        return health_premium(income, schedule)

    def _l10n_ca_prov_reduction(self, vals, prefix, income, tax):
        """S = min(T4 + V1, 2 x (S2 + Y) - (T4 + V1)), at least 0, Y the
        amount per dependant times the dependants of the contract."""
        if prefix != "l10n_ca.on":
            return super()._l10n_ca_prov_reduction(vals, prefix, income, tax)
        factor_y = (
            self._l10n_ca_prov_param(vals, prefix, "tax_reduction_dependant")
            * vals["contract"]._l10n_ca_on_dependants()
        )
        basic = self._l10n_ca_prov_param(vals, prefix, "tax_reduction_basic")
        return tax_reduction(tax, basic, factor_y)
