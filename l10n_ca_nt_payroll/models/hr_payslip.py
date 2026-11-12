# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Northwest Territories on the common provincial engine of l10n_ca_payroll.

The engine computes the Northwest Territories income tax (T4127 option 1,
steps 4 to 6) and the WSCC assessment from the parameters
``l10n_ca.nt.*``. The territory has no factor of its own in T4127 and no
employer payroll tax.

The Northwest Territories payroll tax is borne by the employee and withheld
by the employer (Payroll Tax Act, s. 3(1) and 5(1)): this module adds it to
the amounts of the pay as ``nt_payroll_tax``, which the salary rule
CA_NT_PAYROLL_TAX deducts.
"""

from odoo import _, api, models
from odoo.tools import float_round

PREFIX = "l10n_ca.nt"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "NT": PREFIX}

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "NT":
            return _("WSCC Assessment (Northwest Territories)")
        return super()._l10n_ca_wcb_name(province)

    def _l10n_ca_compute_other_contributions(self, vals):
        """Also the Northwest Territories payroll tax of the pay.

        For a contract in the Northwest Territories: ``nt_payroll_tax`` =
        ``l10n_ca.nt.payroll_tax.rate`` x G rounded to the cent, G the
        gross of the pay with its sign; 0 for a contract exempt from the
        tax. The amount is positive; the salary rule gives it its negative
        sign. A credit note has the amount of the pay it takes back, which
        its negative count in the totals reverses. ``nt_payroll_tax_rate``
        keeps the rate applied.
        """
        vals = super()._l10n_ca_compute_other_contributions(vals)
        if vals["province"].code != "NT":
            return vals
        rate = 0.0
        if not vals["contract"].l10n_ca_nt_payroll_tax_exempt:
            rate = self._l10n_ca_prov_param(vals, PREFIX, "payroll_tax.rate", 0.0)
        vals.update(
            {
                "nt_payroll_tax_rate": rate,
                "nt_payroll_tax": float_round(rate * vals["gross"], precision_digits=2),
            }
        )
        return vals
