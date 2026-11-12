# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Ontario income tax and employer contributions.

The federal module calls the extension points overridden here for an
employment in Ontario (province code ON):

- ``_l10n_ca_compute_other_contributions``: Employer Health Tax (EHT) and
  WSIB premium of the pay, employer costs that withhold nothing;
- ``_l10n_ca_provincial_tax``: Ontario income tax per T4127 option 1 for
  the regular pay (steps 4 and 5) and for the non-periodic payments (TB).

The Ontario tax reuses the annual taxable income A of the federal step
(``federal_annual_income``), which is already net of F, F2, U1 and F5A,
and the K2 items of the federal module with the lowest Ontario rate
(K2P). Those items raise the maximum of the base CPP credit by the QPP
withheld before a transfer out of Quebec, so K2P is then the K2RP of
T4127. The amounts land in the ``vals`` dictionary of ``_l10n_ca_compute``
under ``on_*`` keys, read by the Ontario salary rules.
"""

from odoo import _, models
from odoo.tools import float_round
from odoo.tools.misc import formatLang

from odoo.addons.l10n_ca_time_parameter.tools import bracket_constant, marginal_rate

from ..tools import health_premium, lowest_rate, surtax, tax_reduction


def _round(amount):
    return float_round(amount, precision_digits=2)


def _is_ontario(province):
    return province.code == "ON"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # ------------------------------------------------------------------
    # Year-to-date amounts
    # ------------------------------------------------------------------

    def _l10n_ca_on_previous_domain(self, date):
        """Return the domain of the payslips counted before this one.

        Payslips of the company paid from January 1 to ``date``, this
        payslip excluded: outside a batch, the done ones; in a batch, the
        done ones of other batches and the not cancelled ones of the same
        batch that come before this payslip, whatever their state. Within
        the batch, payslips are ordered by (pay date, id): a peer comes
        before when its pay date is earlier, or the same with a lower id. A
        payslip of the batch counts by its lines, so once it is computed.
        Each pair of payslips of a batch is thus counted once, by the later
        one, whatever order the batch is confirmed in.
        """
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("l10n_ca_pay_date", ">=", date.replace(month=1, day=1)),
            ("l10n_ca_pay_date", "<=", date),
            ("id", "!=", self.id),
        ]
        run = self.payslip_run_id.id
        if not run:
            return [*domain, ("state", "=", "done")]
        return [
            *domain,
            "|",
            "&",
            ("state", "=", "done"),
            ("payslip_run_id", "!=", run),
            "&",
            "&",
            ("payslip_run_id", "=", run),
            ("state", "!=", "cancel"),
            # With the pay date <= date of the outer domain: an earlier
            # pay date, or the same one with a lower id.
            "|",
            ("l10n_ca_pay_date", "<", date),
            ("id", "<", self.id),
        ]

    def _l10n_ca_on_line_total(self, slip_domain, code):
        """Return the signed total of rule ``code`` on ``slip_domain``.

        Refunds count negatively. Two SQL sums on the payslip lines, one
        per sign, so no line is read into Python.
        """
        total = 0.0
        for credit_note, sign in ((False, 1.0), (True, -1.0)):
            [(amount,)] = self.env["hr.payslip.line"]._read_group(
                [
                    ("code", "=", code),
                    (
                        "slip_id",
                        "any",
                        [*slip_domain, ("credit_note", "=", credit_note)],
                    ),
                ],
                aggregates=["total:sum"],
            )
            total += sign * (amount or 0.0)
        return total

    def _l10n_ca_on_ytd(self, date):
        """Return the Ontario year-to-date amounts of the employee.

        ``wsib_insurable`` sums rule CA_ON_WSIB_IE and ``salary`` rule
        CA_ON_SAL of the payslips of the employee counted before this one
        (``_l10n_ca_on_previous_domain``), so two payslips of the employee
        in one batch share the annual maximum.
        """
        domain = [
            ("employee_id", "=", self.employee_id.id),
            *self._l10n_ca_on_previous_domain(date),
        ]
        return {
            "wsib_insurable": self._l10n_ca_on_line_total(domain, "CA_ON_WSIB_IE"),
            "salary": self._l10n_ca_on_line_total(domain, "CA_ON_SAL"),
        }

    def _l10n_ca_on_company_payroll_ytd(self, date):
        """Return the Ontario remuneration the company paid before this pay.

        Sums rule CA_ON_SAL, refunds negatively, of the payslips of the
        company counted before this one (``_l10n_ca_on_previous_domain``).
        """
        return self._l10n_ca_on_line_total(
            self._l10n_ca_on_previous_domain(date), "CA_ON_SAL"
        )

    # ------------------------------------------------------------------
    # Employer contributions
    # ------------------------------------------------------------------

    def _l10n_ca_compute_other_contributions(self, vals):
        """Employer Health Tax and WSIB premium of an Ontario pay.

        EHT = rate x (max(0, R + G - E) - max(0, R - E)): G is the gross of
        the pay, R the Ontario remuneration of the company paid before it
        this year (``_l10n_ca_on_company_payroll_ytd``), E the exemption of
        the company and the rate is the one of the annual total Ontario
        remuneration of the rate basis of the company. The exemption is
        thus consumed by the first pays of the year, and the pays after it
        bear the tax on their whole remuneration. G keeps its sign: a pay
        of negative earnings lowers R and reverses the EHT of the part of
        the remuneration above E it takes back.

        WSIB = rate per $100 x IE / 100, IE = min(G, maximum - IE of the
        year so far) the insurable earnings of the pay, at least 0, and 0
        for a contract not covered by the WSIB.

        A credit note (``credit_note``) takes its gross out of the year:
        its lines count negatively in R and in the year-to-date amounts, so
        its amounts are those that reverse the pay, positive. EHT = rate x
        (max(0, R - E) - max(0, R - G - E)), the tax of the last G of R.
        IE = min(G, IE of the year so far - min(maximum, S - G)), at least
        0, S being the CA_ON_SAL of the employee so far: the insurable
        earnings of the year fall to those of the remuneration left.

        A rate basis left at 0 on the company gives the rate and the
        exemption of a nil remuneration, which the payslip warns about.
        """
        vals = super()._l10n_ca_compute_other_contributions(vals)
        if not _is_ontario(vals["province"]):
            return vals
        company = vals["company"]
        contract = vals["contract"]
        date = vals["date"]
        gross = vals["gross"]
        refund = self.credit_note

        total_payroll = company._l10n_ca_on_eht_payroll()
        if total_payroll <= 0:
            self._l10n_ca_on_warn_eht_basis(vals)
        eht_rate = company._l10n_ca_on_eht_rate(total_payroll, date)
        exemption = company._l10n_ca_on_eht_exemption(total_payroll, date)
        paid = self._l10n_ca_on_company_payroll_ytd(date)
        if refund:
            taxable = max(0.0, paid - exemption) - max(0.0, paid - gross - exemption)
        else:
            taxable = max(0.0, paid + gross - exemption) - max(0.0, paid - exemption)

        ytd = self._l10n_ca_on_ytd(date)
        insurable = 0.0
        if not contract.l10n_ca_on_wsib_exempt:
            maximum = company._l10n_ca_param("l10n_ca.on.wsib.max_insurable", date)
            if refund:
                left = min(maximum, max(0.0, ytd["salary"] - gross))
                insurable = min(gross, ytd["wsib_insurable"] - left)
            else:
                insurable = min(gross, maximum - ytd["wsib_insurable"])
            insurable = max(0.0, insurable)

        vals.update(
            {
                "on_ytd": ytd,
                "on_salary": gross,
                "on_eht_payroll": total_payroll,
                "on_eht_rate": eht_rate,
                "on_eht_exemption": exemption,
                "on_eht_paid": paid,
                "on_eht_taxable": taxable,
                "on_eht": _round(eht_rate * taxable),
                "on_eht_line_name": _(
                    "Ontario Employer Health Tax (%(rate)s%%)",
                    rate=formatLang(self.env, eht_rate * 100, digits=3),
                ),
                "on_wsib_insurable": insurable,
                "on_wsib": _round(insurable * company.l10n_ca_on_wsib_rate / 100),
            }
        )
        return vals

    def _l10n_ca_on_warn_eht_basis(self, vals):
        """Add to ``vals["warnings"]`` that the EHT rate basis is 0.

        Names the amount field of the rate basis selected on the company,
        in the language of the user.
        """
        company = vals["company"]
        field_name = (
            "l10n_ca_on_eht_estimated_payroll"
            if company.l10n_ca_on_eht_basis == "estimate"
            else "l10n_ca_on_eht_previous_payroll"
        )
        message = _(
            'The EHT rate basis of %(company)s, "%(field)s", is 0 in the Ontario '
            "payroll settings: the Employer Health Tax of this payslip uses the "
            "lowest rate and the exemption of a nil remuneration.",
            company=company.name,
            field=company._fields[field_name]._description_string(self.env),
        )
        if message not in vals["warnings"]:
            vals["warnings"].append(message)

    # ------------------------------------------------------------------
    # Ontario income tax
    # ------------------------------------------------------------------

    def _l10n_ca_on_lowest_rate(self, vals):
        """Return the lowest Ontario rate in force at the pay date."""
        brackets = vals["company"]._l10n_ca_param("l10n_ca.on.brackets", vals["date"])
        return lowest_rate(brackets)

    def _l10n_ca_provincial_tax(self, vals):
        """Ontario income tax of the period, T4127 option 1.

        Regular pay: A is the federal annual taxable income, T2 of A per
        ``_l10n_ca_on_annual_tax`` with K2P = K2 of the regular
        contributions at the lowest Ontario rate; tax per period =
        T2 / P rounded to the cent, plus the additional Ontario tax of the
        contract. Non-periodic payments add ``_l10n_ca_on_bonus_tax``. The
        amount is rounded on its own, as the federal module rounds T1 / P,
        where T4127 rounds (T1 + T2) / P once: the total can differ by 0.01.
        A pay of a year without a version of ``l10n_ca.on.bpa`` warns that
        it uses the indexed amounts of an earlier year.
        """
        if not _is_ontario(vals["province"]):
            return super()._l10n_ca_provincial_tax(vals)
        self._l10n_ca_check_indexation(vals, "l10n_ca.on.bpa")
        contract = vals["contract"]
        periods = vals["periods"]
        annual = vals["federal_annual_income"]
        nonperiodic = vals["nonperiodic"]
        regular = vals
        if nonperiodic:
            regular = self._l10n_ca_regular_values(vals, vals["gross"] - nonperiodic)
        lowest = self._l10n_ca_on_lowest_rate(vals)
        annual_tax = self._l10n_ca_on_annual_tax(
            vals, annual, self._l10n_ca_federal_k2(regular, lowest)
        )
        vals.update(
            {
                "on_annual_income": annual,
                "on_basic_tax": annual_tax["basic_tax"],
                "on_surtax": annual_tax["surtax"],
                "on_health_premium": annual_tax["health_premium"],
                "on_tax_reduction": annual_tax["tax_reduction"],
                "on_annual_tax": annual_tax["tax"],
                "on_regular_tax": _round(annual_tax["tax"] / periods),
                "on_bonus_tax": 0.0,
            }
        )
        if nonperiodic:
            self._l10n_ca_on_bonus_tax(vals, regular, lowest)
        return (
            vals["on_regular_tax"]
            + vals["on_bonus_tax"]
            + _round(contract.l10n_ca_on_additional_tax)
        )

    def _l10n_ca_on_annual_tax(self, vals, income, k2p):
        """Return the annual Ontario tax T2 of the annual income ``income``.

        T4 = V x A - KP - K1P - K2P - K3P, at least 0, V and KP being those
        of the bracket of A (KP derived from the table and rounded to the
        dollar like the federal K), K1P = lowest rate x TCP, K3P the other
        Ontario credits of the contract. V1 is the surtax on T4, V2 the
        Ontario Health Premium on A, S = min(T4 + V1, 2 x (S2 + Y) - (T4 +
        V1)) the tax reduction, Y the amount per dependant times the
        dependants of the contract; T2 = T4 + V1 + V2 - S, at least 0. An
        exempt contract (claim code E) only bears V2. A nil or negative A
        bears nothing.

        Returns a dictionary with ``basic_tax`` (T4), ``surtax`` (V1),
        ``health_premium`` (V2), ``tax_reduction`` (S) and ``tax`` (T2).
        """
        result = dict.fromkeys(
            ("basic_tax", "surtax", "health_premium", "tax_reduction", "tax"), 0.0
        )
        if income <= 0:
            return result
        company = vals["company"]
        contract = vals["contract"]
        date = vals["date"]
        param = company._l10n_ca_param
        premium = health_premium(income, param("l10n_ca.on.health_premium", date))
        result.update({"health_premium": premium, "tax": premium})
        if contract.l10n_ca_on_td1_type == "exempt":
            return result
        brackets = param("l10n_ca.on.brackets", date)
        constant = float_round(bracket_constant(income, brackets), precision_digits=0)
        credits = (
            lowest_rate(brackets) * contract._l10n_ca_on_claim(date)
            + k2p
            + contract.l10n_ca_on_other_credits
        )
        basic_tax = max(
            0.0, marginal_rate(income, brackets) * income - constant - credits
        )
        surtax_amount = surtax(basic_tax, param("l10n_ca.on.surtax", date))
        factor_y = (
            param("l10n_ca.on.tax_reduction_dependant", date)
            * contract._l10n_ca_on_dependants()
        )
        reduction = tax_reduction(
            basic_tax + surtax_amount,
            param("l10n_ca.on.tax_reduction_basic", date),
            factor_y,
        )
        result.update(
            {
                "basic_tax": basic_tax,
                "surtax": surtax_amount,
                "tax_reduction": reduction,
                "tax": max(0.0, basic_tax + surtax_amount + premium - reduction),
            }
        )
        return result

    def _l10n_ca_on_bonus_tax(self, vals, regular, lowest):
        """TB, the Ontario tax on the non-periodic payments of the pay.

        Regular bonus calculation of T4127: T2 of A with the payment
        payable now less T2 of A without it, each T2 recomputed in full
        (T4, V1, V2 and S). A with the payment is the one of the federal
        step (``federal_bonus_income``); A without it is P x (I - F - F2 -
        F5A - U1) of the federal step (``federal_bonus_base``) plus B1 -
        F5BYTD of the year. A pay without regular remuneration thus takes I,
        F, F2, U1 and F5A of the most recent regular pay, as the federal
        step does. K2P adds the contributions on the payment
        once, as the federal K2. When A with the payment is at most
        ``l10n_ca.federal.bonus_flat_threshold``, the federal flat rate
        ``l10n_ca.federal.bonus_flat_rate`` is the whole federal and
        provincial withholding on the payment (T4127, 15% outside Quebec)
        and the federal step withholds it: the Ontario TB is 0.
        """
        param = vals["company"]._l10n_ca_param
        date = vals["date"]
        with_payment = vals["federal_bonus_income"]
        tax = 0.0
        if with_payment > param("l10n_ca.federal.bonus_flat_threshold", date):
            ytd = vals["ytd"]
            without = vals["federal_bonus_base"] + max(
                0.0, ytd["nonperiodic"] - ytd["f5b"]
            )
            tax_with = self._l10n_ca_on_annual_tax(
                vals, with_payment, self._l10n_ca_federal_k2(vals, lowest, regular)
            )["tax"]
            tax_without = self._l10n_ca_on_annual_tax(
                vals, without, self._l10n_ca_federal_k2(regular, lowest)
            )["tax"]
            tax = max(0.0, tax_with - tax_without)
        vals.update({"on_bonus_income": with_payment, "on_bonus_tax": _round(tax)})
        return vals
