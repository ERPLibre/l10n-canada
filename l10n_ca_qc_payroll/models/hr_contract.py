# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date as Date

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..tools import round_half_up


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_ca_province_code = fields.Char(related="l10n_ca_province_id.code")
    l10n_ca_qc_claim_type = fields.Selection(
        [
            ("basic", "Basic personal amount"),
            ("custom", "Amounts from the TP-1015.3"),
        ],
        string="Quebec TP-1015.3 Claim",
        default="basic",
        required=True,
        help="Basic personal amount: the personal tax credits are the "
        "Quebec basic personal amount of the year, as for an employee who "
        "files no TP-1015.3 form. Amounts from the TP-1015.3: the amounts "
        "of lines 7 and 9 of the form.",
    )
    l10n_ca_qc_claim_amount = fields.Monetary(
        string="TP-1015.3 Line 7 (Indexed Credits)",
        help="E1 of the TP-1015.F formulas: indexed value of the personal "
        "tax credits, line 7 of form TP-1015.3. 0 for an employee who "
        "claims no credit. A pay of a later year multiplies it by 1 + the "
        "indexation rate of each following year.",
    )
    l10n_ca_qc_claim_year = fields.Integer(
        string="TP-1015.3 Year",
        default=lambda self: fields.Date.context_today(self).year,
        help="Year the TP-1015.3 amounts were declared for. The employee "
        "files no new form for the annual indexation: on a pay of a later "
        "year, line 7 is multiplied by 1 + the rate of the time parameter "
        "l10n_ca.qc.indexation_rate of each year after this one.",
    )
    l10n_ca_qc_claim_non_indexed = fields.Monetary(
        string="TP-1015.3 Line 9 (Non-Indexed Credits)",
        help="E2 of the TP-1015.F formulas: non-indexed value of the "
        "personal tax credits, line 9 of form TP-1015.3.",
    )
    l10n_ca_qc_bpa = fields.Monetary(
        string="Quebec Basic Personal Amount",
        compute="_compute_l10n_ca_qc_bpa",
        help="Quebec basic personal amount in force today.",
    )
    l10n_ca_qc_deductions = fields.Monetary(
        string="TP-1015.3 Line 19 (Annual Deductions)",
        help="J of the TP-1015.F formulas: annual deductions claimed on "
        "line 19 of form TP-1015.3 (for example the deduction for "
        "residents of designated remote areas).",
    )
    l10n_ca_qc_deductions_date = fields.Date(
        string="TP-1015.3 Line 19 Effective Date",
        help="Pay date from which the deductions of line 19 apply. When "
        "it falls after the first pay of its year, the annual amount is "
        "spread over the pays left: P x amount / PR, PR being the pays of "
        "the year left from that date (TP-1015.F, variable J). Empty: the "
        "amount applies from January 1.",
    )
    l10n_ca_qc_authorized_deductions = fields.Monetary(
        string="Deductions Authorized by Revenu Quebec (TP-1016)",
        help="J1 of the TP-1015.F formulas: annual deductions authorized "
        "after an application for a reduction in source deductions "
        "(form TP-1016).",
    )
    l10n_ca_qc_authorized_credits = fields.Monetary(
        string="Credits Authorized by Revenu Quebec (TP-1016)",
        help="K1 of the TP-1015.F formulas: annual non-refundable tax "
        "credits authorized after a TP-1016 application, as a credit "
        "amount.",
    )
    l10n_ca_qc_authorized_date = fields.Date(
        string="TP-1016 Authorization Effective Date",
        help="Pay date from which the deductions and credits authorized by "
        "Revenu Quebec apply. When it falls after the first pay of its "
        "year, each annual amount is spread over the pays left: P x amount "
        "/ PR, PR being the pays of the year left from that date "
        "(TP-1015.F, variables J1 and K1). Empty: the amounts apply from "
        "January 1.",
    )
    l10n_ca_qc_ftq_withholding = fields.Monetary(
        string="Fonds de solidarité FTQ Withholding per Pay",
        help="Q of the TP-1015.F formulas: amount withheld on each pay to "
        "buy class A shares of the Fonds de solidarité FTQ. The Quebec tax "
        "of the year is reduced by 15% x P x Q. The amounts withheld for "
        "the year do not exceed 5,000 $ for both funds. Leave 0 when the "
        "withholding is subtracted from the gross remuneration instead "
        "(TP-1015.G part 3.3.3).",
    )
    l10n_ca_qc_fondaction_withholding = fields.Monetary(
        string="Fondaction Withholding per Pay",
        help="Q1 of the TP-1015.F formulas: amount withheld on each pay to "
        "buy class A or B shares of Fondaction. The Quebec tax of the year "
        "is reduced by 15% x P x Q1. The amounts withheld for the year do "
        "not exceed 5,000 $ for both funds. Leave 0 when the withholding "
        "is subtracted from the gross remuneration instead (TP-1015.G "
        "part 3.3.3).",
    )
    l10n_ca_qc_additional_tax = fields.Monetary(
        string="Additional Quebec Tax per Pay",
        help="L of the TP-1015.F formulas: additional income tax the "
        "employee asks to have withheld on each pay (form TP-1015.3 or "
        "TP-1017).",
    )
    l10n_ca_qc_tax_exempt = fields.Boolean(
        string="Exempt from Quebec Income Tax Withholding",
        help="The employee asked on form TP-1015.3 to be exempt from "
        "source deductions of Quebec income tax for the year.",
    )
    l10n_ca_qc_cnesst_exempt = fields.Boolean(
        string="Not Covered by the CNESST",
        help="No occupational health and safety premium on this "
        "remuneration, e.g. a director of the corporation without "
        "personal coverage.",
    )

    def _compute_l10n_ca_qc_bpa(self):
        today = fields.Date.context_today(self)
        for contract in self:
            company = contract.company_id or self.env.company
            contract.l10n_ca_qc_bpa = company._l10n_ca_param(
                "l10n_ca.qc.bpa", today, default=0.0
            )

    def _l10n_ca_qc_indexation_rate(self, year):
        """Return the Quebec indexation rate of ``year``.

        Only a version of l10n_ca.qc.indexation_rate dated in ``year``
        counts: the rate of an earlier year carried forward would index
        with a wrong rate, so a missing year raises a UserError.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        code = "l10n_ca.qc.indexation_rate"
        version = company._l10n_ca_param_version(code, Date(year, 1, 1))
        if not version or version.date_from.year != year:
            raise UserError(
                _(
                    "No Quebec indexation rate for %(year)s (time parameter "
                    "%(code)s): the TP-1015.3 amounts of the contract "
                    "%(contract)s, declared for %(claim_year)s, cannot be "
                    "indexed. Add the rate of %(year)s, or enter the amounts "
                    "of a TP-1015.3 filed for a later year.",
                    year=year,
                    code=code,
                    contract=self.display_name,
                    claim_year=self.l10n_ca_qc_claim_year,
                )
            )
        return company._l10n_ca_param(code, Date(year, 1, 1))

    def _l10n_ca_qc_claim(self, date):
        """Return E = E1 + E2 of the TP-1015.F formulas at ``date``.

        With the TP-1015.3 amounts, E1 is line 7 multiplied by 1 + the
        indexation rate of each year after the year of the form, up to the
        year of ``date``; E2, line 9, is not indexed. Otherwise E1 is the
        basic personal amount of the year. E is rounded half up to the
        dollar.
        """
        self.ensure_one()
        if self.l10n_ca_qc_claim_type == "custom":
            indexed = self.l10n_ca_qc_claim_amount
            claim_year = self.l10n_ca_qc_claim_year or date.year
            if indexed:
                for year in range(claim_year + 1, date.year + 1):
                    indexed *= 1 + self._l10n_ca_qc_indexation_rate(year)
        else:
            indexed = (self.company_id or self.env.company)._l10n_ca_param(
                "l10n_ca.qc.bpa", date
            )
        return round_half_up(indexed + self.l10n_ca_qc_claim_non_indexed, 0)
