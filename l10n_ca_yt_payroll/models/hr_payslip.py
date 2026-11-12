# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Yukon on the common provincial engine of l10n_ca_payroll.

The engine computes the Yukon income tax (T4127 option 1, steps 4 to 6)
and the WSCB assessment from the parameters ``l10n_ca.yt.*``. Yukon adds
two factors of its own: the basic personal amount BPAYT, which mirrors the
federal BPAF and so decreases with the net income, and the territorial
Canada employment credit K4P. Yukon has no employer payroll tax and no
labour-sponsored funds credit.
"""

from odoo import _, api, models

from odoo.addons.l10n_ca_payroll.models.hr_payslip_province import lowest_rate

PREFIX = "l10n_ca.yt"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_province_prefixes(self):
        return {**super()._l10n_ca_province_prefixes(), "YT": PREFIX}

    @api.model
    def _l10n_ca_wcb_name(self, province):
        if province.code == "YT":
            return _("WSCB Assessment")
        return super()._l10n_ca_wcb_name(province)

    def _l10n_ca_prov_bpa(self, vals, prefix, income):
        """BPAYT = BPAF of the net income NI = A + HD.

        The federal amount, its phase-out and its rounding to the cent
        (``_l10n_ca_federal_bpa``): the maximum up to the start of the
        phase-out, the minimum from its end. ``l10n_ca.yt.bpa`` holds the
        maximum only, for the contract and the indexation check.
        """
        if prefix != PREFIX:
            return super()._l10n_ca_prov_bpa(vals, prefix, income)
        net_income = income + vals["contract"].l10n_ca_prescribed_zone_deduction
        return self._l10n_ca_federal_bpa(vals["company"], net_income, vals["date"])

    def _l10n_ca_prov_extra_credits(self, vals, prefix, income, k1p, k2p):
        """K4P = min(V x A*, V x CEA), V the lowest Yukon rate.

        A* is the annual gross employment income, P x the gross of the pay
        without its non-periodic payments; CEA the federal Canada
        employment amount (``l10n_ca.federal.canada_employment_amount``),
        which T4127 table 8.2 also gives for Yukon. Yukon has no K5P.
        """
        credits = super()._l10n_ca_prov_extra_credits(vals, prefix, income, k1p, k2p)
        if prefix != PREFIX:
            return credits
        company = vals["company"]
        date = vals["date"]
        rate = lowest_rate(company._l10n_ca_param(f"{PREFIX}.brackets", date))
        employment_income = vals["periods"] * (vals["gross"] - vals["nonperiodic"])
        amount = company._l10n_ca_param(
            "l10n_ca.federal.canada_employment_amount", date
        )
        return credits + max(0.0, min(rate * employment_income, rate * amount))
