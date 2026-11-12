# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Newfoundland and Labrador on the common provincial engine of
l10n_ca_payroll.

The engine computes the Newfoundland and Labrador income tax (T4127 option
1, steps 4 to 6), the Health and Post-Secondary Education Tax and the
WorkplaceNL assessment from the parameters ``l10n_ca.nl.*``. The province
has no factor of its own: no surtax, premium, reduction or labour-sponsored
funds credit. The basic personal amount is a dated parameter whose version
of July 1, 2026 carries the prorated amount of the second half of 2026.
"""

from odoo import _, api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "NL": "l10n_ca.nl"}

    @api.model
    def _l10n_ca_employer_tax_name(self, province):
        if province.code == "NL":
            return _("Health and Post-Secondary Education Tax")
        return super()._l10n_ca_employer_tax_name(province)

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "NL":
            return _("WorkplaceNL Assessment")
        return super()._l10n_ca_wcb_name(province)

    def _l10n_ca_warn_employer_tax_basis(self, vals, account):
        """Warn only when the rate basis selects something.

        For Newfoundland and Labrador, ``l10n_ca.nl.employer_tax.rates``
        with a single rate and no
        ``l10n_ca.nl.employer_tax.exemption_threshold`` make the tax
        independent of the total remuneration of the company: a basis left
        at 0 gives the tax of any other basis and the payslip does not
        warn. A version of the parameters that adds a rate or a threshold
        restores the warning.
        """
        prefix = self._l10n_ca_province_prefix(vals["province"])
        if prefix == "l10n_ca.nl":
            rates = self._l10n_ca_prov_param(vals, prefix, "employer_tax.rates")
            threshold = self._l10n_ca_prov_param(
                vals, prefix, "employer_tax.exemption_threshold"
            )
            if len(rates) == 1 and threshold is None:
                return
        return super()._l10n_ca_warn_employer_tax_basis(vals, account)
