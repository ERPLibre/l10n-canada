# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Alberta on the common provincial engine of l10n_ca_payroll.

The engine computes the Alberta income tax (T4127 option 1, steps 4 to 6)
and the WCB-Alberta premium from the parameters ``l10n_ca.ab.*``. Alberta
adds one factor of its own, the supplemental tax credit K5P; it has no
employer payroll tax and no labour-sponsored funds tax credit.
"""

from odoo import _, api, models

PREFIX = "l10n_ca.ab"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "AB": PREFIX}

    def _l10n_ca_prov_extra_credits(self, vals, prefix, income, k1p, k2p):
        """Return K5P, the Alberta supplemental tax credit.

        K5P = ((K1P + K2P) - threshold) x rate, at least 0 (T4127, step 4,
        Alberta), with ``l10n_ca.ab.supplemental_credit.threshold`` and
        ``.rate`` of the pay date. K1P and K2P are valued at the lowest
        rate (8%): the credit adds the difference between the second rate
        and the lowest one on the credit amounts above the top of the
        first bracket (T4032-AB: 2% of the amounts above 61,200 in 2026).
        K3P, the other credits of the contract, does not count.
        """
        credits = super()._l10n_ca_prov_extra_credits(vals, prefix, income, k1p, k2p)
        if prefix != PREFIX:
            return credits
        param = vals["company"]._l10n_ca_param
        threshold = param(f"{PREFIX}.supplemental_credit.threshold", vals["date"])
        rate = param(f"{PREFIX}.supplemental_credit.rate", vals["date"])
        return credits + max(0.0, (k1p + k2p - threshold) * rate)

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "AB":
            return _("WCB-Alberta Premium")
        return super()._l10n_ca_wcb_name(province)
