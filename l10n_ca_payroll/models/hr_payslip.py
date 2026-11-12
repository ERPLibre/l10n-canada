# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Canadian statutory deductions computed per the CRA T4127 formulas.

The salary rules of the "Canada - Base" structure read their amounts from
``hr.payslip._l10n_ca_compute``. That method runs a sequence of steps on a
``vals`` dictionary; each step and each ``_l10n_ca_*`` method named below
is an extension point for a provincial module:

- ``_l10n_ca_pension_plan(province)``: "cpp" or "qpp"; the pension
  parameters are read under ``l10n_ca.<plan>.``.
- ``_l10n_ca_ei_rate(date, province)``: employee EI rate.
- ``_l10n_ca_compute_other_contributions(vals)``: provincial
  contributions computed before the income tax.
- ``_l10n_ca_federal_k2_items(vals)``: contributions that give the
  federal K2 credit; a provincial module adds its own.
- ``_l10n_ca_federal_abatement(province, date)``: abatement rate applied
  to the basic federal tax.
- ``_l10n_ca_provincial_tax(vals)``: provincial tax for the period, or
  None when the province has no calculation, which the payslip reports as
  a warning instead of a silent zero.

Bonuses, retroactive pay increases and other non-periodic payments are the
rules of category ``CA_LUMP`` (B of the formulas), less the deductions of
category ``CA_LUMP_DED`` withheld from them (F3). They are part of the
gross: the contributions apply to the whole pay, while the income tax
annualizes only the regular part I = gross - B and taxes B with the bonus
formulas.

The RPP, RRSP and similar contributions withheld from the regular pay are
the rules of category ``CA_TAX_DED`` (F of the formulas). They lower the
taxable income of the pay, not its pensionable or insurable earnings.
"""

import math
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round

from odoo.addons.l10n_ca_time_parameter.tools import bracket_constant, marginal_rate

from .hr_contract import SCHEDULE_PAY_PERIODS

# Rule codes whose year-to-date totals depend on the pension plan.
PENSION_CODES = (
    "CA_PE",
    "CA_CPP",
    "CA_CPP2",
    "CA_CPP_ER",
    "CA_CPP2_ER",
    "CA_F5B",
)

# Salary rule categories of the non-periodic payments (B), of the
# deductions withheld from them (F3) and of the deductions withheld from
# the regular pay that lower its taxable income (F).
NONPERIODIC_CATEGORY = "CA_LUMP"
NONPERIODIC_DEDUCTION_CATEGORY = "CA_LUMP_DED"
TAX_DEDUCTION_CATEGORY = "CA_TAX_DED"


def _round(amount):
    return float_round(amount, precision_digits=2)


class L10nCaPayrollRuleHelper:
    """Object exposed as ``l10n_ca`` to the code of the salary rules.

    ``get(contract, gross)`` returns the dictionary of
    ``hr.payslip._l10n_ca_compute`` and computes it once per contract,
    gross, non-periodic payments and deductions: the statutory rules each
    read one key without recomputing the year-to-date totals.
    ``categories`` is the object of the category totals of the payslip
    being computed, from which the non-periodic payments and the
    deductions F3 and F are read. A
    helper is built for each payslip computation, so a recomputation never
    reads the values of the previous one.
    """

    def __init__(self, payslip, categories=None):
        self.payslip = payslip
        self.categories = categories
        self.cache = {}

    def _category_total(self, code):
        if self.categories is None:
            return 0.0
        return self.categories.dict.get(code, 0.0)

    def get(self, contract, gross):
        nonperiodic = self._category_total(NONPERIODIC_CATEGORY)
        deductions = -self._category_total(NONPERIODIC_DEDUCTION_CATEGORY)
        tax_deductions = -self._category_total(TAX_DEDUCTION_CATEGORY)
        key = (
            contract.id,
            _round(gross),
            _round(nonperiodic),
            _round(deductions),
            _round(tax_deductions),
        )
        if key not in self.cache:
            self.cache[key] = self.payslip._l10n_ca_compute(
                contract, gross, nonperiodic, deductions, tax_deductions
            )
        return self.cache[key]

    def period_wage(self, contract):
        return self.payslip._l10n_ca_period_wage(contract)

    def warnings(self):
        result = []
        for vals in self.cache.values():
            for warning in vals["warnings"]:
                if warning not in result:
                    result.append(warning)
        return result


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_ca_pay_date = fields.Date(
        string="Pay Date",
        compute="_compute_l10n_ca_pay_date",
        store=True,
        index=True,
        help="Date the remuneration is paid: the accounting date of the "
        "payslip, else its end date. It selects the calendar year of the "
        "maximums and the remittance period.",
    )
    l10n_ca_province_id = fields.Many2one(
        "res.country.state",
        string="Province of Employment",
        readonly=True,
        copy=True,
    )
    l10n_ca_pension_plan = fields.Selection(
        [("cpp", "CPP"), ("qpp", "QPP")],
        string="Pension Plan",
        readonly=True,
        copy=True,
    )
    l10n_ca_warning = fields.Text(
        string="Canadian Payroll Warning",
        readonly=True,
        copy=False,
    )

    @api.depends("date", "date_to")
    def _compute_l10n_ca_pay_date(self):
        for slip in self:
            slip.l10n_ca_pay_date = slip.date or slip.date_to

    # ------------------------------------------------------------------
    # Hooks of the OCA payroll engine
    # ------------------------------------------------------------------

    def compute_sheet(self):
        for slip in self:
            contract = slip.contract_id or slip._get_employee_contracts()[:1]
            province = contract.l10n_ca_province_id
            slip.write(
                {
                    "l10n_ca_province_id": province.id,
                    "l10n_ca_pension_plan": (
                        slip._l10n_ca_pension_plan(province) if province else False
                    ),
                    "l10n_ca_warning": False,
                }
            )
        return super().compute_sheet()

    def _get_baselocaldict(self, contracts):
        localdict = super()._get_baselocaldict(contracts)
        localdict["l10n_ca"] = L10nCaPayrollRuleHelper(self, localdict["categories"])
        return localdict

    def localdict_hook(self, localdict):
        localdict = super().localdict_hook(localdict)
        helper = localdict.get("l10n_ca")
        if isinstance(helper, L10nCaPayrollRuleHelper):
            warnings = helper.warnings()
            if warnings:
                self.l10n_ca_warning = "\n".join(warnings)
        return localdict

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _l10n_ca_pension_plan(self, province):
        """Return the pension plan of an employment in ``province``."""
        return "qpp" if province.code == "QC" else "cpp"

    def _l10n_ca_ei_rate(self, date, province):
        """Return the employee EI rate; Quebec has a reduced rate."""
        code = "l10n_ca.ei.rate_qc" if province.code == "QC" else "l10n_ca.ei.rate"
        return self.company_id._l10n_ca_param(code, date)

    def _l10n_ca_federal_abatement(self, province, date):
        """Return the rate that reduces the basic federal tax T3."""
        if province.code == "QC":
            return self.company_id._l10n_ca_param("l10n_ca.federal.qc_abatement", date)
        return 0.0

    def _l10n_ca_provincial_tax(self, vals):
        """Return the provincial tax of the period, None if not computed."""
        return

    def _l10n_ca_provincial_tax_collected_by_cra(self, province):
        """Return whether the CRA collects the provincial tax.

        Quebec collects its own income tax: it is neither remitted on the
        PD7A nor reported in box 22 of the T4.
        """
        return province.code != "QC"

    def _l10n_ca_compute_other_contributions(self, vals):
        """Add provincial contributions to ``vals`` before the income tax."""
        return vals

    def _l10n_ca_federal_k2_items(self, vals):
        """Return the contributions of the pay that give the K2 credit.

        A dictionary of items {"period": amount of the pay the credit
        counts, "reached": whether the annual maximum is reached in this
        pay or a previous one, "maximum": annual maximum of the credited
        amount}. ``_l10n_ca_federal_k2`` turns them into the credit: the
        base part of the CPP/QPP contribution and the EI premium here.
        """
        params = vals["pension_params"]
        months = vals["pension_months"]
        max_base = _round(
            (params["ympe"] - params["basic_exemption"]) * params["base_rate"]
        )
        max_pension = vals["pension_max"] * months / 12
        return {
            "pension": {
                "period": vals["cpp"] * params["base_rate"] / params["rate"],
                "reached": bool(max_pension)
                and vals["cpp"] + vals["ytd"]["cpp"] >= max_pension - 0.005,
                "maximum": max_base * months / 12,
            },
            "ei": {
                "period": vals["ei"],
                "reached": bool(vals["ei_max"])
                and vals["ei"] + vals["ytd"]["ei"] >= vals["ei_max"] - 0.005,
                "maximum": vals["ei_max"],
            },
        }

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def _l10n_ca_period_wage(self, contract):
        """Return the salary of one pay period; ``wage`` is monthly."""
        periods = contract.l10n_ca_pay_periods or 12
        return _round(contract.wage * 12 / periods)

    @api.model
    def _l10n_ca_federal_bpa(self, company, net_income, date):
        """Return the federal basic personal amount for ``net_income``.

        The amount is the maximum up to the phase-out start, the minimum
        from the phase-out end, and decreases linearly in between (BPAF of
        the T4127 formulas).
        """
        param = company._l10n_ca_param
        bpa_max = param("l10n_ca.federal.bpa_max", date)
        bpa_min = param("l10n_ca.federal.bpa_min", date)
        start = param("l10n_ca.federal.bpa_phaseout_start", date)
        end = param("l10n_ca.federal.bpa_phaseout_end", date)
        if net_income <= start:
            return bpa_max
        if net_income >= end:
            return bpa_min
        return _round(
            bpa_max - (net_income - start) * (bpa_max - bpa_min) / (end - start)
        )

    def _l10n_ca_ytd(self, date, plan):
        """Return the year-to-date amounts of the employee at ``date``.

        Sums the lines of the done payslips of the same employee and
        company whose pay date falls in the calendar year of ``date``, on
        or before it, other than this payslip. Refunds count negatively.
        Pension codes only count the payslips of the same plan. Deductions
        are returned as positive amounts.
        """
        self.ensure_one()
        slips = self.search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("company_id", "=", self.company_id.id),
                ("state", "=", "done"),
                ("l10n_ca_pay_date", ">=", date.replace(month=1, day=1)),
                ("l10n_ca_pay_date", "<=", date),
                ("id", "!=", self.id),
            ]
        )
        totals = slips._l10n_ca_line_totals(plan=plan)
        return {
            "pensionable": totals["CA_PE"],
            "insurable": totals["CA_IE"],
            "cpp": -totals["CA_CPP"],
            "cpp2": -totals["CA_CPP2"],
            "ei": -totals["CA_EI"],
            "nonperiodic": totals["CA_NPP"],
            "f5b": totals["CA_F5B"],
        }

    def _l10n_ca_line_totals(self, plan=None):
        """Return the signed totals per rule code of these payslips.

        With ``plan``, the pension codes only count the payslips of that
        plan.
        """
        totals = defaultdict(float)
        for slip in self:
            sign = -1.0 if slip.credit_note else 1.0
            pension_ok = plan is None or slip.l10n_ca_pension_plan == plan
            for line in slip.line_ids:
                if line.code in PENSION_CODES and not pension_ok:
                    continue
                totals[line.code] += sign * line.total
        return totals

    def _l10n_ca_compute(
        self, contract, gross, nonperiodic=0.0, deductions=0.0, tax_deductions=0.0
    ):
        """Return the statutory amounts of ``contract`` for ``gross``.

        ``nonperiodic`` is the part of ``gross`` paid as bonuses or other
        non-periodic payments (B), ``deductions`` the deductions withheld
        from them (F3), ``tax_deductions`` the deductions withheld from the
        regular pay that lower its taxable income (F). Amounts are positive
        and rounded to the cent; the salary rules give the deductions their
        negative sign.
        """
        self.ensure_one()
        vals = self._l10n_ca_prepare_values(
            contract, gross, nonperiodic, deductions, tax_deductions
        )
        self._l10n_ca_compute_contributions(vals)
        self._l10n_ca_compute_federal_tax(vals)
        self._l10n_ca_compute_provincial_tax(vals)
        return vals

    def _l10n_ca_compute_contributions(self, vals):
        self._l10n_ca_compute_pension(vals)
        self._l10n_ca_compute_ei(vals)
        self._l10n_ca_compute_other_contributions(vals)
        self._l10n_ca_compute_nonperiodic_share(vals)
        return vals

    def _l10n_ca_regular_values(self, vals, gross):
        """Return the amounts of a pay of ``gross`` without bonus.

        The contributions of that pay are the regular contributions that
        the bonus formulas annualize in K2; the year-to-date amounts are
        those of ``vals``.
        """
        regular = dict(
            vals,
            gross=gross,
            nonperiodic=0.0,
            nonperiodic_deductions=0.0,
            nonperiodic_net=0.0,
            warnings=[],
        )
        return self._l10n_ca_compute_contributions(regular)

    def _l10n_ca_prepare_values(
        self, contract, gross, nonperiodic=0.0, deductions=0.0, tax_deductions=0.0
    ):
        province = contract.l10n_ca_province_id
        if not province:
            raise UserError(
                _(
                    "Set the province of employment on the contract "
                    "%(contract)s to compute the Canadian deductions.",
                    contract=contract.display_name,
                )
            )
        date = self.l10n_ca_pay_date or self.date or self.date_to
        plan = self._l10n_ca_pension_plan(province)
        nonperiodic = min(max(nonperiodic, 0.0), max(gross, 0.0))
        deductions = min(max(deductions, 0.0), nonperiodic)
        tax_deductions = min(max(tax_deductions, 0.0), max(gross - nonperiodic, 0.0))
        return {
            "company": self.company_id,
            "contract": contract,
            "date": date,
            "province": province,
            "periods": contract.l10n_ca_pay_periods
            or SCHEDULE_PAY_PERIODS.get(contract.schedule_pay, 12),
            "gross": gross,
            "nonperiodic": nonperiodic,
            "nonperiodic_deductions": deductions,
            "nonperiodic_net": _round(nonperiodic - deductions),
            "tax_deductions": _round(tax_deductions),
            "plan": plan,
            "pension_label": plan.upper(),
            "line_names": self._l10n_ca_pension_line_names(plan),
            "ytd": self._l10n_ca_ytd(date, plan),
            "warnings": [],
        }

    def _l10n_ca_pension_line_names(self, plan):
        """Return the payslip line names of the pension rules for ``plan``.

        The salary rules give them as ``result_name``, keyed by rule code,
        so a payslip line reads in the language of the user who computes
        it and names the plan of the employee.
        """
        if plan == "qpp":
            return {
                "CA_CPP": _("QPP Contributions"),
                "CA_CPP2": _("QPP2 Contributions"),
                "CA_CPP_ER": _("QPP Employer Contributions"),
                "CA_CPP2_ER": _("QPP2 Employer Contributions"),
            }
        return {
            "CA_CPP": _("CPP Contributions"),
            "CA_CPP2": _("CPP2 Contributions"),
            "CA_CPP_ER": _("CPP Employer Contributions"),
            "CA_CPP2_ER": _("CPP2 Employer Contributions"),
        }

    def _l10n_ca_pension_params(self, company, plan, date):
        prefix = f"l10n_ca.{plan}."
        if company._l10n_ca_param(prefix + "rate", date, default=None) is None:
            raise UserError(
                _(
                    "No %(plan)s contribution rate in force on %(date)s "
                    "(time parameter %(code)s). The QPP rates of the "
                    "employees working in Quebec come with the Quebec "
                    "payroll module.",
                    plan=plan.upper(),
                    date=date,
                    code=prefix + "rate",
                )
            )

        def param(key, default=None, required=True):
            if required:
                return company._l10n_ca_param(prefix + key, date)
            return company._l10n_ca_param(prefix + key, date, default=default)

        return {
            "ympe": param("ympe"),
            "yampe": param("yampe"),
            "basic_exemption": param("basic_exemption"),
            "rate": param("rate"),
            "base_rate": param("base_rate"),
            "rate2": param("rate2"),
            "age_min": param("age_min", required=False),
            "age_max": param("age_max", required=False),
        }

    def _l10n_ca_pension_months(self, vals, params):
        """Return (contributes this pay, PM) for the pension plan.

        PM is the number of months of the calendar year during which
        contributions are required: from the month after the minimum age
        is reached to the month the maximum age is reached, inclusive.
        """
        if vals["contract"].l10n_ca_cpp_exempt:
            return False, 0
        date = vals["date"]
        start = date.replace(month=1, day=1)
        end = date.replace(month=12, day=31)
        birthday = self.employee_id.birthday
        if birthday and params["age_min"] is not None:
            start = max(
                start,
                birthday + relativedelta(years=int(params["age_min"]), months=1, day=1),
            )
        if birthday and params["age_max"] is not None:
            end = min(
                end, birthday + relativedelta(years=int(params["age_max"]), day=31)
            )
        if start > end:
            return False, 0
        months = end.month - start.month + 1
        return start <= date <= end, months

    def _l10n_ca_compute_pension(self, vals):
        """CPP/QPP base and first additional (C) and second additional (C2).

        C = min(max * PM/12 - D, rate * (PI - exemption / P)), the exemption
        per period being truncated to the cent as in the CRA tables.
        C2 = min(max2 * PM/12 - D2, (PIYTD + PI - W) * rate2) with
        W = max(PIYTD, YMPE * PM/12). D and D2 also count the contributions
        withheld this year under the plan the employee was transferred
        from (see ``_l10n_ca_pension_transfer_ytd``); PIYTD only sums the
        payslips of the current plan. The employer pays the same amounts.
        """
        params = self._l10n_ca_pension_params(
            vals["company"], vals["plan"], vals["date"]
        )
        applies, months = self._l10n_ca_pension_months(vals, params)
        periods = vals["periods"]
        ytd = vals["ytd"]
        transfer = self._l10n_ca_pension_transfer_ytd(vals, params)
        pensionable = vals["gross"] if applies else 0.0
        cpp = cpp2 = 0.0
        max_cpp = _round((params["ympe"] - params["basic_exemption"]) * params["rate"])
        if pensionable > 0:
            exemption = math.floor(params["basic_exemption"] / periods * 100) / 100
            cpp = min(
                max_cpp * months / 12 - (transfer["cpp"] + ytd["cpp"]),
                params["rate"] * (pensionable - exemption),
            )
            cpp = max(0.0, _round(cpp))
            max_cpp2 = _round((params["yampe"] - params["ympe"]) * params["rate2"])
            ceiling = max(ytd["pensionable"], params["ympe"] * months / 12)
            cpp2 = min(
                max_cpp2 * months / 12 - (transfer["cpp2"] + ytd["cpp2"]),
                (ytd["pensionable"] + pensionable - ceiling) * params["rate2"],
            )
            cpp2 = max(0.0, _round(cpp2))
        vals.update(
            {
                "pension_params": params,
                "pension_months": months,
                "pension_transfer": transfer,
                "pension_max": max_cpp,
                "pensionable": pensionable,
                "cpp": cpp,
                "cpp2": cpp2,
                "cpp_employer": cpp,
                "cpp2_employer": cpp2,
            }
        )
        return vals

    def _l10n_ca_pension_transfer_ytd(self, vals, params):
        """Return the contributions withheld under the plan transferred from.

        An employee transferred during the year from a CPP establishment
        to a QPP one has the CPP withheld since the start of the year
        count against the QPP maximums, converted by the ratio of the
        rates: R * (QPP rate / CPP rate) for the base and first additional
        contribution, R2 * (QPP rate2 / CPP rate2) for the second
        additional one (TP-1015.F), rounded to the cent like the amounts
        withheld, so that the maximum less these amounts leaves no residue
        below the cent once reached. ``params`` are the pension parameters
        of the current plan. Returns {"cpp": ..., "cpp2": ...}, zero for a
        CPP payslip and for an employee without CPP payslips this year.
        """
        transfer = {"cpp": 0.0, "cpp2": 0.0}
        if vals["plan"] != "qpp":
            return transfer
        other = self._l10n_ca_ytd(vals["date"], "cpp")
        if not (other["cpp"] or other["cpp2"]):
            return transfer
        cpp_params = self._l10n_ca_pension_params(vals["company"], "cpp", vals["date"])
        transfer["cpp"] = _round(other["cpp"] * params["rate"] / cpp_params["rate"])
        transfer["cpp2"] = _round(other["cpp2"] * params["rate2"] / cpp_params["rate2"])
        return transfer

    def _l10n_ca_compute_ei(self, vals):
        """EI = min(max premium - D1, rate * IE); employer = multiplier * EI.

        The maximum premium is the maximum insurable earnings times the
        rate. A reduced multiplier set on the company replaces the legal
        one.
        """
        company = vals["company"]
        date = vals["date"]
        rate = self._l10n_ca_ei_rate(date, vals["province"])
        max_ei = _round(company._l10n_ca_param("l10n_ca.ei.mie", date) * rate)
        insurable = 0.0 if vals["contract"].l10n_ca_ei_exempt else vals["gross"]
        ei = 0.0
        if insurable > 0:
            ei = max(0.0, _round(min(max_ei - vals["ytd"]["ei"], rate * insurable)))
        multiplier = company.l10n_ca_ei_employer_multiplier or company._l10n_ca_param(
            "l10n_ca.ei.employer_multiplier", date
        )
        vals.update(
            {
                "insurable": insurable,
                "ei_rate": rate,
                "ei_max": max_ei,
                "ei": ei,
                "ei_employer": _round(ei * multiplier),
            }
        )
        return vals

    def _l10n_ca_compute_nonperiodic_share(self, vals):
        """F5 of the pay and its share F5B on the non-periodic payments.

        F5 = C * (rate - base rate) / rate + C2, the first and second
        additional contributions of the pay; F5B = F5 * B / PI (T4127),
        which TP-1015.F calls CSB. A pay without pensionable earnings has
        no F5B.
        """
        params = vals["pension_params"]
        f5 = vals["cpp"] * (params["rate"] - params["base_rate"]) / params["rate"]
        f5 += vals["cpp2"]
        pensionable = vals["pensionable"]
        f5b = 0.0
        if vals["nonperiodic"] and pensionable > 0:
            f5b = _round(f5 * min(vals["nonperiodic"], pensionable) / pensionable)
        vals.update({"f5": f5, "f5b": f5b})
        return vals

    def _l10n_ca_federal_k2(self, vals, credit_rate, regular=None):
        """Return K2, the federal credit of the contributions of the pay.

        Each item of ``_l10n_ca_federal_k2_items`` gives min(P * amount,
        maximum), and the maximum once it is reached. With ``regular``, the
        values of the same pay without its non-periodic payments, only the
        regular amount is annualized and the share of the non-periodic
        payments is added once: min(P * regular + (amount - regular),
        maximum), as in the bonus example of T4127.
        """
        periods = vals["periods"]
        items = self._l10n_ca_federal_k2_items(vals)
        regular_items = (
            items if regular is None else self._l10n_ca_federal_k2_items(regular)
        )
        total = 0.0
        for key, item in items.items():
            if item["reached"]:
                total += item["maximum"]
                continue
            base = regular_items[key]["period"]
            total += min(
                periods * base + max(0.0, item["period"] - base), item["maximum"]
            )
        return credit_rate * total

    def _l10n_ca_federal_annual_tax(self, vals, annual, employment_income, k2):
        """Return (TC, T3, T1) for the annual taxable income ``annual``.

        T3 = R * A - K - K1 - K2 - K3 - K4, K being the constant of the
        bracket rounded to the dollar as in the CRA tables, K4 the credit
        of the Canada employment amount on ``employment_income``;
        T1 = T3 - abatement * T3.
        """
        company = vals["company"]
        contract = vals["contract"]
        date = vals["date"]
        param = company._l10n_ca_param
        brackets = param("l10n_ca.federal.brackets", date)
        credit_rate = param("l10n_ca.federal.credit_rate", date)
        rate = marginal_rate(annual, brackets)
        constant = float_round(bracket_constant(annual, brackets), precision_digits=0)
        claim = contract._l10n_ca_federal_claim(annual, date)
        k1 = credit_rate * claim
        k3 = contract.l10n_ca_federal_other_credits
        k4 = min(
            credit_rate * employment_income,
            credit_rate * param("l10n_ca.federal.canada_employment_amount", date),
        )
        basic_tax = max(0.0, rate * annual - constant - k1 - k2 - k3 - k4)
        abatement = self._l10n_ca_federal_abatement(vals["province"], date)
        return claim, basic_tax, max(0.0, basic_tax - abatement * basic_tax)

    def _l10n_ca_compute_federal_tax(self, vals):
        """Federal tax per period, T4127 option 1.

        Regular pay: A = P * (I - F - F5A), I = gross - B, F the deductions
        of category CA_TAX_DED, F5A = F5 * (PI - B) / PI; tax per period =
        T1 / P + L. The Canada employment amount counts P * I, before F.
        Non-periodic payments add TB (``_l10n_ca_federal_bonus_tax``).
        """
        company = vals["company"]
        contract = vals["contract"]
        periods = vals["periods"]
        nonperiodic = vals["nonperiodic"]
        regular_gross = vals["gross"] - nonperiodic
        f5a = vals["f5"]
        if nonperiodic and vals["pensionable"] > 0:
            f5a = vals["f5"] * (vals["pensionable"] - nonperiodic) / vals["pensionable"]
        regular = vals
        if nonperiodic:
            regular = self._l10n_ca_regular_values(vals, regular_gross)
        additional = _round(contract.l10n_ca_additional_federal_tax)
        annual = periods * (regular_gross - vals["tax_deductions"] - f5a)
        vals.update(
            {
                "federal_annual_income": annual,
                "federal_regular_tax": 0.0,
                "federal_bonus_tax": 0.0,
            }
        )
        if annual > 0:
            credit_rate = company._l10n_ca_param(
                "l10n_ca.federal.credit_rate", vals["date"]
            )
            k2 = self._l10n_ca_federal_k2(regular, credit_rate)
            claim, basic_tax, annual_tax = self._l10n_ca_federal_annual_tax(
                vals, annual, periods * regular_gross, k2
            )
            vals.update(
                {
                    "federal_claim": claim,
                    "federal_basic_tax": basic_tax,
                    "federal_annual_tax": annual_tax,
                    "federal_regular_tax": _round(annual_tax / periods),
                }
            )
        if nonperiodic:
            self._l10n_ca_federal_bonus_tax(vals, regular, f5a)
        vals["federal_tax"] = (
            vals["federal_regular_tax"] + vals["federal_bonus_tax"] + additional
        )
        return vals

    def _l10n_ca_federal_bonus_tax(self, vals, regular, f5a):
        """TB, the federal tax on the non-periodic payments of the pay.

        Regular bonus calculation of T4127: TB = T1 of A with the payment
        payable now less T1 of A without it, where
        A = P * (I - F - F5A) + (B - F3 - F5B) + (B1 - F5BYTD), the last term
        dropped without the payment. B1 and F5BYTD are the year-to-date
        totals of rules CA_NPP and CA_F5B. K2 adds the contributions on
        the payment once (``_l10n_ca_federal_k2``). When A with the
        payment is at most ``l10n_ca.federal.bonus_flat_threshold``, TB is
        the flat rate of the payment less F3, a rate of its own in Quebec.
        """
        company = vals["company"]
        date = vals["date"]
        periods = vals["periods"]
        param = company._l10n_ca_param
        regular_gross = regular["gross"]
        base = max(0.0, periods * (regular_gross - vals["tax_deductions"] - f5a))
        payment = max(0.0, vals["nonperiodic_net"] - vals["f5b"])
        previous = max(0.0, vals["ytd"]["nonperiodic"] - vals["ytd"]["f5b"])
        with_payment = base + payment + previous
        flat_rate_code = (
            "l10n_ca.federal.bonus_flat_rate_qc"
            if vals["province"].code == "QC"
            else "l10n_ca.federal.bonus_flat_rate"
        )
        if with_payment <= param("l10n_ca.federal.bonus_flat_threshold", date):
            bonus_tax = param(flat_rate_code, date) * vals["nonperiodic_net"]
        else:
            credit_rate = param("l10n_ca.federal.credit_rate", date)
            income = periods * regular_gross + vals["ytd"]["nonperiodic"]
            tax_with = self._l10n_ca_federal_annual_tax(
                vals,
                with_payment,
                income + vals["nonperiodic_net"],
                self._l10n_ca_federal_k2(vals, credit_rate, regular),
            )[2]
            tax_without = self._l10n_ca_federal_annual_tax(
                vals,
                base + previous,
                income,
                self._l10n_ca_federal_k2(regular, credit_rate),
            )[2]
            bonus_tax = max(0.0, tax_with - tax_without)
        vals.update(
            {
                "federal_bonus_income": with_payment,
                "federal_bonus_tax": _round(bonus_tax),
            }
        )
        return vals

    def _l10n_ca_compute_provincial_tax(self, vals):
        province = vals["province"]
        tax = self._l10n_ca_provincial_tax(vals)
        if tax is None:
            vals["provincial_tax"] = 0.0
            vals["provincial_tax_label"] = _(
                "Provincial income tax NOT COMPUTED (%(province)s)",
                province=province.name,
            )
            vals["warnings"].append(
                _(
                    "Provincial income tax is not computed for %(province)s: "
                    "no calculation for this province is installed. The "
                    "payslip withholds no provincial tax.",
                    province=province.name,
                )
            )
        else:
            vals["provincial_tax"] = _round(tax)
            vals["provincial_tax_label"] = _(
                "Provincial Income Tax (%(province)s)", province=province.code
            )
        return vals

    # ------------------------------------------------------------------
    # Year-end and remittances
    # ------------------------------------------------------------------

    def _l10n_ca_t4_values(self, year):
        """Return the T4 boxes of these payslips (one employee, province).

        Box 24 is capped at the maximum insurable earnings and box 26 at
        the second earnings ceiling (YAMPE) of ``year``.
        """
        if not self:
            return {}
        company = self[:1].company_id
        year_end = fields.Date.to_date(f"{year}-12-31")
        province = self[:1].l10n_ca_province_id
        totals = self._l10n_ca_line_totals()
        cpp = self.filtered(lambda s: s.l10n_ca_pension_plan == "cpp")
        qpp = self.filtered(lambda s: s.l10n_ca_pension_plan == "qpp")
        cpp_totals = cpp._l10n_ca_line_totals()
        qpp_totals = qpp._l10n_ca_line_totals()
        income_tax = -totals["CA_FIT"]
        if self._l10n_ca_provincial_tax_collected_by_cra(province):
            income_tax -= totals["CA_PIT"]
        plan = (qpp or cpp)[:1].l10n_ca_pension_plan or "cpp"
        yampe = company._l10n_ca_param(f"l10n_ca.{plan}.yampe", year_end, default=None)
        mie = company._l10n_ca_param("l10n_ca.ei.mie", year_end, default=None)
        pensionable = totals["CA_PE"]
        insurable = totals["CA_IE"]
        contracts = self.contract_id
        return {
            "province_code": province.code,
            "box_14": totals["GROSS"],
            "box_16": -cpp_totals["CA_CPP"],
            "box_16a": -cpp_totals["CA_CPP2"],
            "box_17": -qpp_totals["CA_CPP"],
            "box_17a": -qpp_totals["CA_CPP2"],
            "box_18": -totals["CA_EI"],
            "box_20": -totals["CA_RPP"],
            "box_22": income_tax,
            "box_24": min(insurable, mie) if mie is not None else insurable,
            "box_26": min(pensionable, yampe) if yampe is not None else pensionable,
            "box_44": -totals["CA_UNION"],
            "box_45": contracts.sorted("date_start")[-1:].l10n_ca_t4_dental_code or "1",
            "cpp_exempt": not pensionable
            and any(contracts.mapped("l10n_ca_cpp_exempt")),
            "ei_exempt": not insurable and any(contracts.mapped("l10n_ca_ei_exempt")),
            "employer_cpp": cpp_totals["CA_CPP_ER"],
            "employer_cpp2": cpp_totals["CA_CPP2_ER"],
            "employer_ei": totals["CA_EI_ER"],
        }

    def _l10n_ca_remittance_values(self):
        """Return the amounts these payslips add to a CRA remittance (PD7A).

        QPP contributions and the Quebec income tax are remitted to Revenu
        Quebec and are left out.
        """
        cpp = self.filtered(lambda s: s.l10n_ca_pension_plan == "cpp")
        cpp_totals = cpp._l10n_ca_line_totals()
        totals = self._l10n_ca_line_totals()
        income_tax = -totals["CA_FIT"]
        for slip in self:
            if slip._l10n_ca_provincial_tax_collected_by_cra(slip.l10n_ca_province_id):
                income_tax -= slip._l10n_ca_line_totals()["CA_PIT"]
        # The PD7A counts the employees of the last pay period of each
        # payroll: a monthly and a bi-weekly payroll both count, even when
        # their last pay dates differ.
        employees = self.env["hr.employee"]
        for group in self.grouped(lambda s: s.contract_id.l10n_ca_pay_periods).values():
            last_date = max(group.mapped("l10n_ca_pay_date"))
            employees |= group.filtered(
                lambda s, day=last_date: s.l10n_ca_pay_date == day
            ).employee_id
        return {
            "payslip_count": len(self),
            "employee_count": len(employees),
            "gross_payroll": totals["GROSS"],
            "cpp_employee": -cpp_totals["CA_CPP"],
            "cpp_employer": cpp_totals["CA_CPP_ER"],
            "cpp2_employee": -cpp_totals["CA_CPP2"],
            "cpp2_employer": cpp_totals["CA_CPP2_ER"],
            "ei_employee": -totals["CA_EI"],
            "ei_employer": totals["CA_EI_ER"],
            "income_tax": income_tax,
        }
