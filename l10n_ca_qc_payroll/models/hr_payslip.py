# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Quebec deductions and contributions per the Revenu Quebec formulas.

The federal module calls the extension points overridden here for an
employment in Quebec (province code QC):

- ``_l10n_ca_pension_months``: the QPP stops after December 31 of the year
  the employee reaches ``l10n_ca.qpp.last_contribution_age``;
- ``_l10n_ca_compute_pension``: a QPP contribution above 0 but below half
  a cent is withheld as 0.01 (TP-1015.F part 3.1);
- ``_l10n_ca_compute_other_contributions``: QPIP employee and employer
  premiums (TP-1015.F part 4), Health Services Fund (part 5), labour
  standards (CNT), CNESST and WSDRF contributions;
- ``_l10n_ca_federal_k2_items``: federal credit of the QPIP premium;
- ``_l10n_ca_provincial_tax``: Quebec income tax for regular payments
  (TP-1015.F section 2.1.1) and for bonuses, retroactive payments and
  other similar lump-sum payments (section 2.1.2, the method of the
  company);
- ``_l10n_ca_t4_values``: T4 boxes 55 and 56.

The amounts land in the ``vals`` dictionary of ``_l10n_ca_compute`` under
``qc_*`` and ``qpip*`` keys, read by the Quebec salary rules.

F of TP-1015.F is the total of the rules of category ``CA_TAX_DED`` of the
federal module (RPP, RRSP, PRPP, VRSP), which is also F of T4127, plus the
rules of category ``CA_QC_TAXDED``, the deductions that only Quebec
subtracts. Both run before the statutory rules: the rule helper of this
module reads ``CA_QC_TAXDED`` from the category totals of the payslip being
computed and passes it in the context key ``l10n_ca_qc_tax_deductions``.
"""

import math
from collections import defaultdict

from odoo import _, fields, models
from odoo.tools import float_round
from odoo.tools.misc import formatLang

from odoo.addons.l10n_ca_payroll.models.hr_contract import SCHEDULE_PAY_PERIODS
from odoo.addons.l10n_ca_payroll.models.hr_payslip import (
    NONPERIODIC_CATEGORY,
    L10nCaPayrollRuleHelper,
)
from odoo.addons.l10n_ca_payroll.models.hr_payslip import (
    TAX_DEDUCTION_CATEGORY as FEDERAL_TAX_DEDUCTION_CATEGORY,
)
from odoo.addons.l10n_ca_time_parameter.tools import marginal_rate

from ..tools import quebec_constant

# Salary rule category of the deductions that lower the Quebec taxable
# income only; with the federal CA_TAX_DED they make F of TP-1015.F.
TAX_DEDUCTION_CATEGORY = "CA_QC_TAXDED"


def _round(amount):
    return float_round(amount, precision_digits=2)


def _round_min_cent(amount):
    """Round a QPP contribution or QPIP premium to the cent, at least 0.01.

    A half cent rounds up; an amount above 0 but below 0.005 is withheld
    as 0.01 (TP-1015.F parts 3.1 and 4.1); a negative amount is 0. The
    amount is first rounded to six decimals, so the float residue of a
    maximum less the amounts withheld (about 1e-10 once the maximum is
    reached) counts as 0.
    """
    amount = float_round(amount, precision_digits=6)
    if 0 < amount < 0.005:
        return 0.01
    return max(0.0, _round(amount))


def _category_codes(category):
    """Return the codes of ``category`` and of its parent categories."""
    codes = set()
    while category:
        codes.add(category.code)
        category = category.parent_id
    return codes


def _is_quebec(province):
    return province.code == "QC"


class L10nCaQcPayrollRuleHelper(L10nCaPayrollRuleHelper):
    """Rule helper that also passes the Quebec-only deductions of F.

    ``categories`` is the object of the category totals of the payslip
    being computed. When a rule asks for the statutory amounts, the total
    of category ``CA_QC_TAXDED`` so far, made positive, reaches
    ``hr.payslip._l10n_ca_compute`` in the context key
    ``l10n_ca_qc_tax_deductions``.
    """

    def get(self, contract, gross):
        deductions = -self._category_total(TAX_DEDUCTION_CATEGORY)
        self.payslip = self.payslip.with_context(
            l10n_ca_qc_tax_deductions=max(0.0, deductions)
        )
        return super().get(contract, gross)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _get_baselocaldict(self, contracts):
        localdict = super()._get_baselocaldict(contracts)
        localdict["l10n_ca"] = L10nCaQcPayrollRuleHelper(self, localdict["categories"])
        return localdict

    # ------------------------------------------------------------------
    # Year-to-date amounts
    # ------------------------------------------------------------------

    def _l10n_ca_qc_year_slips(self, date, employee=True):
        """Return the done payslips of the calendar year of ``date``.

        Same selection as the federal year-to-date amounts: the company of
        this payslip, a pay date from January 1 to ``date``, this payslip
        excluded; with ``employee``, only the payslips of its employee.
        """
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            ("l10n_ca_pay_date", ">=", date.replace(month=1, day=1)),
            ("l10n_ca_pay_date", "<=", date),
            ("id", "!=", self.id),
        ]
        if employee:
            domain.append(("employee_id", "=", self.employee_id.id))
        return self.search(domain)

    def _l10n_ca_qc_ytd(self, date):
        """Return the Quebec year-to-date amounts of the employee.

        ``qpip`` and ``qpip_employer`` are the premiums withheld and paid
        (A6 and A7 of TP-1015.F), ``salary`` the remuneration subject to
        the employer contributions (rule CA_QC_SAL), which caps the CNT
        and CNESST bases.
        """
        totals = self._l10n_ca_qc_year_slips(date)._l10n_ca_line_totals()
        return {
            "qpip": -totals["CA_QPIP"],
            "qpip_employer": totals["CA_QPIP_ER"],
            "salary": totals["CA_QC_SAL"],
        }

    def _l10n_ca_qc_period_slips(self, date_from, date_to):
        """Return the other payslips of the company paid in a date range.

        The done payslips with a pay date from ``date_from`` to ``date_to``,
        plus the payslips of the same batch that are not cancelled, this
        payslip excluded. A payslip of the batch counts by its lines, so
        only once it is computed.
        """
        self.ensure_one()
        state = [("state", "=", "done")]
        if self.payslip_run_id:
            state = [
                "|",
                ("state", "=", "done"),
                "&",
                ("payslip_run_id", "=", self.payslip_run_id.id),
                ("state", "!=", "cancel"),
            ]
        return self.search(
            [
                ("company_id", "=", self.company_id.id),
                ("l10n_ca_pay_date", ">=", date_from),
                ("l10n_ca_pay_date", "<=", date_to),
                ("id", "!=", self.id),
                *state,
            ]
        )

    def _l10n_ca_qc_total_payroll(self, date, gross):
        """Return the total payroll that sets the periodic HSF rate.

        With the year-to-date basis of a new employer, it is the payroll
        paid from January 1 to the end of the Revenu Quebec remittance
        period of ``date`` (TP-1015.G part 6.5): the payslips of the
        company, all provinces, this pay included, plus the payroll of the
        associated employers entered on the company. Otherwise it is the
        total payroll of the previous year entered on the company.
        """
        company = self.company_id
        if company.l10n_ca_qc_hsf_basis == "year_to_date":
            period_end = self.env[
                "l10n_ca.qc.payroll.remittance"
            ]._l10n_ca_qc_period_end(company, date)
            slips = self._l10n_ca_qc_period_slips(
                date.replace(month=1, day=1), period_end
            )
            return (
                slips._l10n_ca_line_totals()["GROSS"]
                + gross
                + company.l10n_ca_qc_associated_payroll
            )
        return company.l10n_ca_qc_total_payroll_estimate

    def _l10n_ca_qc_wsdrf_payroll(self, date, gross):
        """Return the payroll compared with the WSDRF threshold.

        It is the remuneration of the company alone that is subject to the
        contribution (TP-1015.G chapter 8, RL-1 summary line 71), without
        the associated employers nor the remuneration paid outside Quebec.
        With the year-to-date basis, it is the Quebec remuneration of the
        done payslips of the company from January 1 up to this pay, this
        pay included; otherwise the amount of the previous year entered on
        the company.
        """
        company = self.company_id
        if company.l10n_ca_qc_hsf_basis == "year_to_date":
            slips = self._l10n_ca_qc_year_slips(date, employee=False)
            return slips._l10n_ca_line_totals()["CA_QC_SAL"] + gross
        return company.l10n_ca_qc_wsdrf_payroll_estimate

    def _l10n_ca_qc_annualized(self, vals, amount, start):
        """Return J, J1 or K1 of TP-1015.F for an annual ``amount``.

        ``start`` is the pay date from which the amount applies, or empty
        for January 1. A pay before ``start`` gets 0. When ``start`` falls
        in the year of the pay after a first pay of that year, the amount
        is P x amount / PR, PR being P less the done payslips of the
        employee paid in the year before ``start`` (at least 1).
        """
        date = vals["date"]
        if not amount or not start or start.year < date.year:
            return amount
        if start > date:
            return 0.0
        paid = self.search_count(
            [
                ("employee_id", "=", self.employee_id.id),
                ("company_id", "=", self.company_id.id),
                ("state", "=", "done"),
                ("credit_note", "=", False),
                ("l10n_ca_pay_date", ">=", date.replace(month=1, day=1)),
                ("l10n_ca_pay_date", "<", start),
                ("id", "!=", self.id),
            ]
        )
        if not paid:
            return amount
        periods = vals["periods"]
        return periods * amount / max(periods - paid, 1)

    # ------------------------------------------------------------------
    # Extension points of the federal module
    # ------------------------------------------------------------------

    def _l10n_ca_pension_months(self, vals, params):
        applies, months = super()._l10n_ca_pension_months(vals, params)
        birthday = self.employee_id.birthday
        if vals["plan"] != "qpp" or not months or not birthday:
            return applies, months
        last_age = vals["company"]._l10n_ca_param(
            "l10n_ca.qpp.last_contribution_age", vals["date"], default=None
        )
        if last_age is not None and vals["date"].year - birthday.year > last_age:
            return False, 0
        return applies, months

    def _l10n_ca_prepare_values(
        self,
        contract,
        gross,
        nonperiodic=0.0,
        deductions=0.0,
        tax_deductions=0.0,
        federal_deductions=0.0,
    ):
        vals = super()._l10n_ca_prepare_values(
            contract, gross, nonperiodic, deductions, tax_deductions, federal_deductions
        )
        vals["qc_tax_deductions"] = self.env.context.get(
            "l10n_ca_qc_tax_deductions", 0.0
        )
        return vals

    def _l10n_ca_compute_pension(self, vals):
        """Withhold 0.01 for a QPP contribution above 0 but below 0.005.

        The federal step rounds C and C2 half up to the cent; for the QPP,
        a C or C2 rounded to 0 is recomputed unrounded, with the formulas
        of that step (CPP withheld before a transfer to Quebec included),
        and goes through ``_round_min_cent``. The employer
        contributions follow the employee ones (TP-1015.F part 3.2).
        """
        vals = super()._l10n_ca_compute_pension(vals)
        pensionable = vals["pensionable"]
        if vals["plan"] != "qpp" or pensionable <= 0:
            return vals
        params = vals["pension_params"]
        months = vals["pension_months"]
        ytd = vals["ytd"]
        transfer = vals["pension_transfer"]
        if not vals["cpp"]:
            periods = vals["periods"]
            exemption = math.floor(params["basic_exemption"] / periods * 100) / 100
            vals["cpp"] = vals["cpp_employer"] = _round_min_cent(
                min(
                    vals["pension_max"] * months / 12 - (transfer["cpp"] + ytd["cpp"]),
                    params["rate"] * (pensionable - exemption),
                )
            )
        if not vals["cpp2"]:
            max_cpp2 = _round((params["yampe"] - params["ympe"]) * params["rate2"])
            ceiling = max(ytd["pensionable"], params["ympe"] * months / 12)
            vals["cpp2"] = vals["cpp2_employer"] = _round_min_cent(
                min(
                    max_cpp2 * months / 12 - (transfer["cpp2"] + ytd["cpp2"]),
                    (ytd["pensionable"] + pensionable - ceiling) * params["rate2"],
                )
            )
        return vals

    def _l10n_ca_compute_other_contributions(self, vals):
        """QPIP premiums and the Quebec employer contributions.

        QPIP: Ap = min(max - A6, rate * S4) for the employee, withheld as
        0.01 when above 0 but below 0.005, and Ap1 = min(max employer - A7,
        employer rate * S4) for the employer, rounded half up only; the
        maximum is the maximum insurable earnings times the rate.
        HSF = W% * S2, W from the total payroll and the sector of the
        company. CNT and CNESST apply up to their maximum remuneration per
        employee and year; WSDRF accrues when the payroll of the company
        subject to it exceeds its threshold.
        """
        vals = super()._l10n_ca_compute_other_contributions(vals)
        if not _is_quebec(vals["province"]):
            return vals
        company = vals["company"]
        contract = vals["contract"]
        date = vals["date"]
        gross = max(vals["gross"], 0.0)
        param = company._l10n_ca_param
        ytd = self._l10n_ca_qc_ytd(date)

        mie = param("l10n_ca.qpip.mie", date)
        rate = param("l10n_ca.qpip.rate", date)
        employer_rate = param("l10n_ca.qpip.employer_rate", date)
        max_qpip = _round(mie * rate)
        max_qpip_employer = _round(mie * employer_rate)
        qpip = qpip_employer = 0.0
        if gross:
            qpip = _round_min_cent(min(max_qpip - ytd["qpip"], rate * gross))
            qpip_employer = max(
                0.0,
                _round(
                    min(
                        max_qpip_employer - ytd["qpip_employer"],
                        employer_rate * gross,
                    )
                ),
            )

        total_payroll = self._l10n_ca_qc_total_payroll(date, gross)
        hsf_rate = company._l10n_ca_qc_hsf_rate(total_payroll, date)

        cnt = 0.0
        if not company.l10n_ca_qc_cnt_exempt:
            cnt_max = param("l10n_ca.qc.cnt.max_remuneration", date)
            cnt_base = max(0.0, min(gross, cnt_max - ytd["salary"]))
            cnt = _round(cnt_base * param("l10n_ca.qc.cnt.rate", date))

        cnesst = 0.0
        cnesst_rate = company.l10n_ca_qc_cnesst_rate
        if cnesst_rate and not contract.l10n_ca_qc_cnesst_exempt:
            cnesst_max = param("l10n_ca.qc.cnesst.max_insurable", date)
            cnesst_base = max(0.0, min(gross, cnesst_max - ytd["salary"]))
            cnesst = _round(cnesst_base * cnesst_rate / 100)

        wsdrf = 0.0
        wsdrf_payroll = self._l10n_ca_qc_wsdrf_payroll(date, gross)
        if wsdrf_payroll > param("l10n_ca.qc.wsdrf.payroll_threshold", date):
            wsdrf = _round(gross * param("l10n_ca.qc.wsdrf.rate", date))

        vals.update(
            {
                "qc_ytd": ytd,
                "qc_salary": gross,
                "qpip": qpip,
                "qpip_max": max_qpip,
                "qpip_employer": qpip_employer,
                "qc_total_payroll": total_payroll,
                "qc_wsdrf_payroll": wsdrf_payroll,
                "qc_hsf_rate": hsf_rate,
                "qc_hsf": _round(gross * hsf_rate / 100),
                "qc_hsf_line_name": _(
                    "Health Services Fund (%(rate)s%%)",
                    rate=formatLang(self.env, hsf_rate, digits=2),
                ),
                "qc_cnt": cnt,
                "qc_cnesst": cnesst,
                "qc_wsdrf": wsdrf,
            }
        )
        return vals

    def _l10n_ca_federal_k2_items(self, vals):
        """Add the QPIP premium to the federal K2 credit (K2Q of T4127).

        The premium of the pay, up to the maximum premium, and the maximum
        once it is reached in the year.
        """
        items = super()._l10n_ca_federal_k2_items(vals)
        if "qpip" not in vals:
            return items
        max_qpip = vals["qpip_max"]
        items["qpip"] = {
            "period": vals["qpip"],
            "reached": bool(max_qpip)
            and vals["qpip"] + vals["qc_ytd"]["qpip"] >= max_qpip - 0.005,
            "maximum": max_qpip,
        }
        return items

    def _l10n_ca_qc_worker_deduction(self, vals, salary):
        """H = min(rate * D, maximum / P), D the regular salary of the pay."""
        if salary <= 0:
            return 0.0
        param = vals["company"]._l10n_ca_param
        date = vals["date"]
        return _round(
            min(
                param("l10n_ca.qc.worker_deduction_rate", date) * salary,
                param("l10n_ca.qc.worker_deduction_max", date) / vals["periods"],
            )
        )

    def _l10n_ca_provincial_tax(self, vals):
        """Quebec income tax of the period, TP-1015.F section 2.1.

        Regular payments (2.1.1): I = P * (G - F - H - CSA) - J - J1, G
        being the gross less the lump-sum payments B2 of the pay, F the
        rules of categories CA_TAX_DED and CA_QC_TAXDED of the period
        (``tax_deductions`` and ``qc_tax_deductions``), H = min(0.06 * G,
        maximum / P) the deduction for workers, on G before F, and
        CSA = CS * (S3 - B2) / S3 the share of G in CS, the first and second
        additional QPP contributions of the period. J, J1 and K1 are spread
        over the pays left when they apply from a date after the first pay of
        the year (``_l10n_ca_qc_annualized``). Y = T * I - K - K1 - 0.14 * E - 0.15
        * P * Q - 0.15 * P * Q1, Q and Q1 the labour-sponsored fund
        withholdings per pay; tax per period = Y / P + L. H and CSA are
        rounded to the cent and K truncated to the dollar, as in the
        examples and tables of the guide. Lump-sum payments add
        ``_l10n_ca_qc_lump_sum_tax``.
        """
        if not _is_quebec(vals["province"]):
            return super()._l10n_ca_provincial_tax(vals)
        contract = vals["contract"]
        if contract.l10n_ca_qc_tax_exempt:
            vals["qc_annual_income"] = 0.0
            return 0.0
        company = vals["company"]
        date = vals["date"]
        periods = vals["periods"]
        nonperiodic = vals["nonperiodic"]
        salary = vals["gross"] - nonperiodic
        param = company._l10n_ca_param
        worker_deduction = self._l10n_ca_qc_worker_deduction(vals, salary)
        additional_qpp = 0.0
        if vals["plan"] == "qpp":
            additional_qpp = vals["f5"]
            pensionable = vals["pensionable"]
            if nonperiodic and pensionable > 0:
                additional_qpp *= (pensionable - nonperiodic) / pensionable
            additional_qpp = _round(additional_qpp)
        tax_deductions = vals["tax_deductions"] + vals.get("qc_tax_deductions", 0.0)
        deductions = self._l10n_ca_qc_annualized(
            vals, contract.l10n_ca_qc_deductions, contract.l10n_ca_qc_deductions_date
        )
        authorized_deductions = self._l10n_ca_qc_annualized(
            vals,
            contract.l10n_ca_qc_authorized_deductions,
            contract.l10n_ca_qc_authorized_date,
        )
        authorized_credits = self._l10n_ca_qc_annualized(
            vals,
            contract.l10n_ca_qc_authorized_credits,
            contract.l10n_ca_qc_authorized_date,
        )
        annual = max(
            0.0,
            periods * (salary - tax_deductions - worker_deduction - additional_qpp)
            - deductions
            - authorized_deductions,
        )
        claim = contract._l10n_ca_qc_claim(date)
        labour_fund = (
            contract.l10n_ca_qc_ftq_withholding
            + contract.l10n_ca_qc_fondaction_withholding
        )
        labour_fund_credit = 0.0
        if labour_fund:
            labour_fund_credit = (
                param("l10n_ca.qc.labour_fund_credit_rate", date)
                * periods
                * labour_fund
            )
        vals.update(
            {
                "qc_tax_deduction_total": tax_deductions,
                "qc_worker_deduction": worker_deduction,
                "qc_additional_qpp": additional_qpp,
                "qc_deductions": deductions,
                "qc_authorized_deductions": authorized_deductions,
                "qc_authorized_credits": authorized_credits,
                "qc_annual_income": annual,
                "qc_claim": claim,
                "qc_labour_fund_credit": labour_fund_credit,
                "qc_lump_sum_tax": 0.0,
            }
        )
        annual_tax = self._l10n_ca_qc_annual_tax(vals, annual)
        vals["qc_annual_tax"] = annual_tax
        tax = _round(annual_tax / periods) + _round(contract.l10n_ca_qc_additional_tax)
        if nonperiodic:
            tax += self._l10n_ca_qc_lump_sum_tax(vals)
        return tax

    def _l10n_ca_qc_annual_tax(self, vals, income):
        """Y = T * I - K - K1 - 0.14 * E - 0.15 * P * (Q + Q1), at least 0.

        T and K are those of the bracket of ``income``, K truncated to the
        dollar; K1, E and the labour-sponsored fund credit are the values of
        the regular computation in ``vals``.
        """
        param = vals["company"]._l10n_ca_param
        date = vals["date"]
        brackets = param("l10n_ca.qc.brackets", date)
        return max(
            0.0,
            marginal_rate(income, brackets) * income
            - quebec_constant(income, brackets)
            - vals["qc_authorized_credits"]
            - param("l10n_ca.qc.credit_rate", date) * vals["qc_claim"]
            - vals["qc_labour_fund_credit"],
        )

    def _l10n_ca_qc_lump_sum_tax(self, vals):
        """Quebec tax on the lump-sum payments of the pay, TP-1015.F 2.1.2.

        B2 is the lump-sum payments of the pay less the deductions withheld
        from them (category CA_LUMP_DED), CSB = CS * B2 / S3 (``f5b``), B1
        and CSB1 the year-to-date totals of rules CA_NPP and CA_F5B. When
        the annual salary and the lump-sum payments of the year total at
        most the basic personal amount, A is
        ``l10n_ca.qc.lump_sum_flat_rate`` times B2. Otherwise the method of
        the company applies: ``_l10n_ca_qc_lump_sum_method_1``, or the
        second method, I = P * (G - F - H - CSA) + B1 + B2 - CSB1 - CSB - J
        - J1 and A = T * (B2 - CSB), T being the rate of the bracket of I and
        F the same as for the regular payments.
        """
        param = vals["company"]._l10n_ca_param
        date = vals["date"]
        periods = vals["periods"]
        salary = vals["gross"] - vals["nonperiodic"]
        payment = vals["nonperiodic_net"]
        previous = vals["ytd"]["nonperiodic"]
        qpp = vals["plan"] == "qpp"
        csb = vals["f5b"] if qpp else 0.0
        csb_previous = vals["ytd"]["f5b"] if qpp else 0.0
        income = max(
            0.0,
            periods
            * (
                salary
                - vals["qc_tax_deduction_total"]
                - vals["qc_worker_deduction"]
                - vals["qc_additional_qpp"]
            )
            + previous
            + payment
            - csb_previous
            - csb
            - vals["qc_deductions"]
            - vals["qc_authorized_deductions"],
        )
        if periods * salary + previous + payment <= param("l10n_ca.qc.bpa", date):
            tax = param("l10n_ca.qc.lump_sum_flat_rate", date) * payment
        elif vals["company"].l10n_ca_qc_lump_sum_method == "1":
            income, tax = self._l10n_ca_qc_lump_sum_method_1(
                vals, payment - csb, previous - csb_previous
            )
        else:
            brackets = param("l10n_ca.qc.brackets", date)
            tax = marginal_rate(income, brackets) * max(0.0, payment - csb)
        tax = _round(tax)
        vals.update({"qc_lump_sum_income": income, "qc_lump_sum_tax": tax})
        return tax

    def _l10n_ca_qc_lump_sum_method_1(self, vals, payment, previous):
        """Return (I1 + B1 + B2 - CSB1 - CSB, A1) of TP-1015.F 2.1.2 method 1.

        ``payment`` is B2 - CSB and ``previous`` B1 - CSB1.
        I1 = (G1 - F1 - H1 - CSA1) + PR * (G - F - H2 - CSA) - J - J1, the
        year-to-date amounts coming from ``_l10n_ca_qc_regular_ytd`` and PR
        being the pays left in the year, this one included;
        H2 = min(0.06 * (B1 + B2 + G1 + D), (maximum - H1) / PR), rounded
        to the cent, D the regular salary of the pay. Y1 is the annual tax
        (``_l10n_ca_qc_annual_tax``) of I1 + B1 - CSB1, Y2 the one of
        I1 + B1 + B2 - CSB1 - CSB, and A1 = Y2 - Y1: a payment that crosses
        a bracket is taxed at both rates.
        """
        param = vals["company"]._l10n_ca_param
        date = vals["date"]
        salary = vals["gross"] - vals["nonperiodic"]
        ytd = self._l10n_ca_qc_regular_ytd(vals)
        remaining = max(vals["periods"] - ytd["paid"], 1)
        worker_deduction = 0.0
        if salary > 0:
            worker_deduction = _round(
                max(
                    0.0,
                    min(
                        param("l10n_ca.qc.worker_deduction_rate", date)
                        * (
                            vals["ytd"]["nonperiodic"]
                            + vals["nonperiodic_net"]
                            + ytd["salary"]
                            + salary
                        ),
                        (
                            param("l10n_ca.qc.worker_deduction_max", date)
                            - ytd["worker_deduction"]
                        )
                        / remaining,
                    ),
                )
            )
        income = max(
            0.0,
            ytd["salary"]
            - ytd["tax_deductions"]
            - ytd["worker_deduction"]
            - ytd["additional_qpp"]
            + remaining
            * (
                salary
                - vals["qc_tax_deduction_total"]
                - worker_deduction
                - vals["qc_additional_qpp"]
            )
            - vals["qc_deductions"]
            - vals["qc_authorized_deductions"],
        )
        without = self._l10n_ca_qc_annual_tax(vals, income + previous)
        with_payment = self._l10n_ca_qc_annual_tax(vals, income + previous + payment)
        vals.update(
            {
                "qc_lump_sum_remaining_pays": remaining,
                "qc_lump_sum_worker_deduction": worker_deduction,
            }
        )
        return income + previous + payment, max(0.0, with_payment - without)

    def _l10n_ca_qc_regular_ytd(self, vals):
        """Return G1, F1, H1 and CSA1 of TP-1015.F 2.1.2 method 1.

        Sums the done Quebec payslips of the employee paid this year before
        this one (``_l10n_ca_qc_year_slips``), refunds negatively:
        ``salary`` (G1) the gross less the rules of category CA_LUMP;
        ``tax_deductions`` (F1) the rules of categories CA_TAX_DED and
        CA_QC_TAXDED; ``worker_deduction`` (H1) the deduction for workers of
        each pay recomputed from its G and its pay periods;
        ``additional_qpp`` (CSA1) the share of G in the additional QPP
        contributions of each QPP pay, CS * (PI - B) / PI rounded to the
        cent. ``paid`` counts the payslips other than refunds.
        """
        result = {
            "salary": 0.0,
            "tax_deductions": 0.0,
            "worker_deduction": 0.0,
            "additional_qpp": 0.0,
            "paid": 0,
        }
        slips = self._l10n_ca_qc_year_slips(vals["date"]).filtered(
            lambda s: _is_quebec(s.l10n_ca_province_id)
        )
        for slip in slips:
            sign = -1.0 if slip.credit_note else 1.0
            if not slip.credit_note:
                result["paid"] += 1
            lump = deductions = 0.0
            totals = defaultdict(float)
            for line in slip.line_ids:
                totals[line.code] += line.total
                codes = _category_codes(line.category_id)
                if NONPERIODIC_CATEGORY in codes:
                    lump += line.total
                if codes & {TAX_DEDUCTION_CATEGORY, FEDERAL_TAX_DEDUCTION_CATEGORY}:
                    deductions -= line.total
            salary = totals["GROSS"] - lump
            pay_date = slip.l10n_ca_pay_date
            periods = slip.contract_id.l10n_ca_pay_periods or SCHEDULE_PAY_PERIODS.get(
                slip.contract_id.schedule_pay, 12
            )
            worker = self._l10n_ca_qc_worker_deduction(
                {"company": slip.company_id, "date": pay_date, "periods": periods},
                salary,
            )
            additional_qpp = 0.0
            pensionable = totals["CA_PE"]
            if slip.l10n_ca_pension_plan == "qpp" and pensionable > 0:
                params = slip._l10n_ca_pension_params(slip.company_id, "qpp", pay_date)
                contributions = (
                    -totals["CA_CPP"]
                    * (params["rate"] - params["base_rate"])
                    / params["rate"]
                    - totals["CA_CPP2"]
                )
                additional_qpp = _round(
                    contributions * (pensionable - lump) / pensionable
                )
            result["salary"] += sign * salary
            result["tax_deductions"] += sign * deductions
            result["worker_deduction"] += sign * worker
            result["additional_qpp"] += sign * additional_qpp
        return result

    # ------------------------------------------------------------------
    # Year-end and remittances
    # ------------------------------------------------------------------

    def _l10n_ca_t4_values(self, year):
        """Add T4 boxes 55 (PPIP premiums) and 56 (PPIP insurable earnings).

        Box 56 is the remuneration subject to QPIP capped at the maximum
        insurable earnings of ``year``.
        """
        vals = super()._l10n_ca_t4_values(year)
        if not self:
            return vals
        totals = self._l10n_ca_line_totals()
        mie = self[:1].company_id._l10n_ca_param(
            "l10n_ca.qpip.mie", fields.Date.to_date(f"{year}-12-31"), default=None
        )
        salary = totals["CA_QC_SAL"]
        vals.update(
            {
                "box_55": -totals["CA_QPIP"],
                "box_56": min(salary, mie) if mie is not None else salary,
            }
        )
        return vals

    def _l10n_ca_qc_rl1_values(self, year):
        """Return the RL-1 boxes and employer amounts of these payslips.

        The payslips belong to one employee working in Quebec. Box G is
        capped at the maximum pensionable earnings, or at the additional
        maximum when a second additional contribution was withheld (box
        B.B); box I at the QPIP maximum insurable earnings. ``cnt_base``
        and ``cnesst_base`` are the remuneration subject to those
        contributions, capped at their maximum per employee.
        """
        if not self:
            return {}
        company = self[:1].company_id
        year_end = fields.Date.to_date(f"{year}-12-31")
        param = company._l10n_ca_param
        totals = self._l10n_ca_line_totals()
        qpp = self.filtered(lambda s: s.l10n_ca_pension_plan == "qpp")
        qpp_totals = qpp._l10n_ca_line_totals()
        box_b_b = -qpp_totals["CA_CPP2"]
        pension_cap = param(
            "l10n_ca.qpp.yampe" if box_b_b else "l10n_ca.qpp.ympe", year_end
        )
        salary = totals["CA_QC_SAL"]
        contracts = self.contract_id
        cnt_base = 0.0
        if not company.l10n_ca_qc_cnt_exempt:
            cnt_base = min(salary, param("l10n_ca.qc.cnt.max_remuneration", year_end))
        cnesst_base = 0.0
        if company.l10n_ca_qc_cnesst_rate and not all(
            contracts.mapped("l10n_ca_qc_cnesst_exempt")
        ):
            cnesst_base = min(
                salary, param("l10n_ca.qc.cnesst.max_insurable", year_end)
            )
        return {
            "box_a": totals["GROSS"],
            "box_b_a": -qpp_totals["CA_CPP"],
            "box_b_b": box_b_b,
            "box_c": -totals["CA_EI"],
            "box_d": -totals["CA_RPP"],
            "box_e": -totals["CA_PIT"],
            "box_f": -self._l10n_ca_reported_union_dues(),
            "box_g": min(qpp_totals["CA_PE"], pension_cap),
            "box_h": -totals["CA_QPIP"],
            "box_i": min(salary, param("l10n_ca.qpip.mie", year_end)),
            "employer_qpp": qpp_totals["CA_CPP_ER"],
            "employer_qpp2": qpp_totals["CA_CPP2_ER"],
            "employer_qpip": totals["CA_QPIP_ER"],
            "hsf": totals["CA_QC_HSF"],
            "cnt": totals["CA_QC_CNT"],
            "cnt_base": cnt_base,
            "cnesst": totals["CA_QC_CNESST"],
            "cnesst_base": cnesst_base,
            "wsdrf": totals["CA_QC_WSDRF"],
        }

    def _l10n_ca_qc_remittance_values(self):
        """Return the amounts these payslips add to a Revenu Quebec remittance.

        Only payslips of an employment in Quebec count. QPP and QPIP carry
        the employee and employer shares; the labour standards and WSDRF
        contributions are paid with the RL-1 summary and are left out.
        """
        slips = self.filtered(lambda s: _is_quebec(s.l10n_ca_province_id))
        qpp_totals = slips.filtered(
            lambda s: s.l10n_ca_pension_plan == "qpp"
        )._l10n_ca_line_totals()
        totals = slips._l10n_ca_line_totals()
        return {
            "payslip_count": len(slips),
            "employee_count": len(slips.employee_id),
            "gross_payroll": totals["GROSS"],
            "qpp": -qpp_totals["CA_CPP"]
            - qpp_totals["CA_CPP2"]
            + qpp_totals["CA_CPP_ER"]
            + qpp_totals["CA_CPP2_ER"],
            "qpip": -totals["CA_QPIP"] + totals["CA_QPIP_ER"],
            "income_tax": -totals["CA_PIT"],
            "hsf": totals["CA_QC_HSF"],
            "cnesst": totals["CA_QC_CNESST"],
        }
