# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""British Columbia on the common provincial engine of l10n_ca_payroll.

The engine computes the British Columbia income tax (T4127 option 1, steps
4 to 6), the Employer Health Tax and the WorkSafeBC premium from the
parameters ``l10n_ca.bc.*``. British Columbia adds to it the BC tax
reduction, factor S of step 5.
"""

from odoo import _, api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "BC": "l10n_ca.bc"}

    @api.model
    def _l10n_ca_employer_tax_name(self, province):
        if province.code == "BC":
            return _("British Columbia Employer Health Tax")
        return super()._l10n_ca_employer_tax_name(province)

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "BC":
            return _("WorkSafeBC Premium")
        return super()._l10n_ca_wcb_name(province)

    def _l10n_ca_prov_reduction(self, vals, prefix, income, tax):
        """Return S, the BC tax reduction of the annual income A ``income``.

        With S2 ``tax_reduction_basic``, the threshold
        ``tax_reduction_threshold``, the rate ``tax_reduction_rate`` and the
        maximum income ``tax_reduction_max_income`` of ``l10n_ca.bc``:
        S = min(T4, S2) when A is at most the threshold; min(T4, S2 - (A -
        threshold) x rate) when A is at most the maximum income; 0 above.
        ``tax`` is T4 (British Columbia has no V1); S is at least 0.
        """
        if prefix != "l10n_ca.bc":
            return super()._l10n_ca_prov_reduction(vals, prefix, income, tax)

        def param(key):
            return self._l10n_ca_prov_param(vals, prefix, key)

        if income > param("tax_reduction_max_income"):
            return 0.0
        excess = max(0.0, income - param("tax_reduction_threshold"))
        reduction = param("tax_reduction_basic") - excess * param("tax_reduction_rate")
        return max(0.0, min(tax, reduction))
