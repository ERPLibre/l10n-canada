# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Employer Health Tax of a British Columbia charitable or non-profit
employer.

The engine of l10n_ca_payroll applies ``l10n_ca.bc.employer_tax.rates``,
``.exemption`` and ``.exemption_threshold``: no tax up to the exemption,
the notch rate on the remuneration above it up to the threshold, the flat
rate on the whole remuneration above the threshold. A charitable or
non-profit employer has the same shape with its own amounts (Employer
Health Tax Act, ss. 20 and 21): ``.charity_rates``, ``.charity_exemption``
and ``.charity_exemption_threshold``, which these methods substitute for an
account marked as a registered charity and not associated.
"""

from odoo import models

from odoo.addons.l10n_ca_time_parameter.tools import marginal_rate

_BC_PREFIX = "l10n_ca.bc"


class L10nCaPayrollProvinceAccount(models.Model):
    _inherit = "l10n_ca.payroll.province.account"

    def _l10n_ca_bc_charity(self, prefix):
        """Return whether the charity amounts of British Columbia apply."""
        return (
            prefix == _BC_PREFIX
            and len(self) == 1
            and self.employer_tax_charity
            and not self.employer_tax_associated
        )

    def _l10n_ca_employer_tax_rate(self, company, prefix, total_payroll, date):
        """For a British Columbia charity, the rate of
        ``l10n_ca.bc.employer_tax.charity_rates``."""
        if not self._l10n_ca_bc_charity(prefix):
            return super()._l10n_ca_employer_tax_rate(
                company, prefix, total_payroll, date
            )
        rates = company._l10n_ca_param(f"{prefix}.employer_tax.charity_rates", date)
        return marginal_rate(max(total_payroll or 0.0, 0.0), rates)

    def _l10n_ca_employer_tax_exemption(self, company, prefix, total_payroll, date):
        """For a British Columbia charity, ``.charity_exemption`` when
        ``total_payroll`` is at most ``.charity_exemption_threshold``, else
        0; 0 for an employer that is not eligible."""
        if not self._l10n_ca_bc_charity(prefix):
            return super()._l10n_ca_employer_tax_exemption(
                company, prefix, total_payroll, date
            )
        if not self.employer_tax_eligible:
            return 0.0
        param = company._l10n_ca_param
        threshold = param(f"{prefix}.employer_tax.charity_exemption_threshold", date)
        if total_payroll > threshold:
            return 0.0
        return param(f"{prefix}.employer_tax.charity_exemption", date)
