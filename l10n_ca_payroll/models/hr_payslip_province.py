# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Common engine of the provinces whose income tax the CRA collects.

A province module registers its province code with the prefix of its
dated parameters (``_l10n_ca_province_prefixes``, e.g. ``{"NB":
"l10n_ca.nb"}``) and supplies:

- ``<prefix>.brackets``: rates V by annual taxable income A, as
  ``[[threshold, rate], ...]`` from 0; KP is derived and rounded to the
  dollar like the federal K;
- ``<prefix>.bpa``: basic personal amount (TCP without a TD1);
- optionally ``<prefix>.credit_rate`` (rate of K1P and K2P when it is not
  the rate of the first bracket), ``<prefix>.lcp_rate`` and
  ``<prefix>.lcp_max`` (labour-sponsored funds tax credit),
  ``<prefix>.employer_tax.rates``, ``.exemption`` and
  ``.exemption_threshold`` (employer payroll tax) and
  ``<prefix>.wcb.max_insurable`` (workers' compensation).

The engine applies T4127 option 1, steps 4 to 6: T4 = V x A - KP - K1P -
K2P - K3P - K4P - K5P and T2 = T4 + V1 + V2 - S - P x LCP, each at least
0. The factors that only some provinces have are hooks returning 0 here:
``_l10n_ca_prov_extra_credits`` (K4P, K5P), ``_l10n_ca_prov_surtax``
(V1), ``_l10n_ca_prov_premium`` (V2) and ``_l10n_ca_prov_reduction`` (S);
``_l10n_ca_prov_bpa`` returns the basic personal amount of an
income-tested province. The amounts land in ``vals`` under ``provincial_*``
keys and, for the employer contributions, ``employer_tax*`` and ``wcb*``.
"""

from odoo import _, api, models
from odoo.tools import float_round
from odoo.tools.misc import formatLang

from odoo.addons.l10n_ca_time_parameter.tools import bracket_constant, marginal_rate


def _round(amount):
    return float_round(amount, precision_digits=2)


def lowest_rate(brackets):
    """Return the rate of the first bracket of ``brackets``."""
    return float(min((float(t), float(r)) for t, r in brackets)[1])


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @api.model
    def _l10n_ca_province_prefixes(self):
        """Return {province code: parameter prefix} of the installed
        province modules that use this engine."""
        return {}

    @api.model
    def _l10n_ca_province_prefix(self, province):
        """Return the parameter prefix of ``province``, or None."""
        return self._l10n_ca_province_prefixes().get(province.code)

    @api.model
    def _l10n_ca_prov_rule_codes(self, province):
        """Return the codes of the salary rules of ``province`` whose
        year-to-date totals the employer contributions read."""
        return {
            "remuneration": f"CA_{province.code}_SAL",
            "wcb_insurable": f"CA_{province.code}_WCB_IE",
        }

    @api.model
    def _l10n_ca_employer_tax_name(self, province):
        """Return the name of the employer payroll tax of ``province``."""
        return _("%(province)s Employer Payroll Tax", province=province.name)

    @api.model
    def _l10n_ca_wcb_name(self, province):
        """Return the name of the workers' compensation premium."""
        return _("Workers' Compensation Premium (%(province)s)", province=province.code)

    def _l10n_ca_prov_param(self, vals, prefix, key, default=None):
        return vals["company"]._l10n_ca_param(
            f"{prefix}.{key}", vals["date"], default=default
        )

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def _l10n_ca_prov_credit_rate(self, vals, prefix):
        """Return the rate of K1P and K2P: ``<prefix>.credit_rate`` or the
        rate of the first bracket."""
        rate = self._l10n_ca_prov_param(vals, prefix, "credit_rate")
        if rate is not None:
            return rate
        brackets = vals["company"]._l10n_ca_param(f"{prefix}.brackets", vals["date"])
        return lowest_rate(brackets)

    def _l10n_ca_prov_bpa(self, vals, prefix, income):
        """Return the basic personal amount for the annual income ``income``.

        ``<prefix>.bpa``; a province whose amount depends on the income
        overrides this method.
        """
        return vals["company"]._l10n_ca_param(f"{prefix}.bpa", vals["date"])

    def _l10n_ca_prov_claim(self, vals, prefix, income):
        """Return TCP: the TD1 amount of the contract or the basic personal
        amount."""
        contract = vals["contract"]
        if contract.l10n_ca_prov_td1_type == "custom":
            return contract.l10n_ca_prov_td1_amount
        return self._l10n_ca_prov_bpa(vals, prefix, income)

    def _l10n_ca_prov_extra_credits(self, vals, prefix, income, k1p, k2p):
        """Return K4P + K5P for the annual income ``income``; 0 here."""
        return 0.0

    def _l10n_ca_prov_surtax(self, vals, prefix, basic_tax):
        """Return V1, the surtax on the basic provincial tax T4; 0 here."""
        return 0.0

    def _l10n_ca_prov_premium(self, vals, prefix, income):
        """Return V2, levied on A whatever the claim; 0 here."""
        return 0.0

    def _l10n_ca_prov_reduction(self, vals, prefix, income, tax):
        """Return S, the reduction of ``tax`` (T4 + V1); 0 here."""
        return 0.0

    def _l10n_ca_prov_lcp(self, vals, prefix):
        """Return P x LCP, the labour-sponsored funds credit of the year.

        LCP = min(``lcp_max``, ``lcp_rate`` x the shares withheld on the
        pay); P x LCP is at most ``lcp_max``, the credit of a whole year.
        The shares are the amount of the contract and the CA_LSVCC input of
        the payslip. 0 for a province without these parameters.
        """
        rate = self._l10n_ca_prov_param(vals, prefix, "lcp_rate")
        if not rate:
            return 0.0
        maximum = self._l10n_ca_prov_param(vals, prefix, "lcp_max", 0.0)
        shares = vals["contract"].l10n_ca_lsvcc_amount + sum(
            self.input_line_ids.filtered(lambda i: i.code == "CA_LSVCC").mapped(
                "amount"
            )
        )
        per_pay = min(maximum, rate * max(0.0, shares))
        return min(maximum, vals["periods"] * per_pay)

    def _l10n_ca_prov_annual_tax(self, vals, prefix, income, k2p):
        """Return the annual provincial tax T2 of the annual income ``income``.

        T4 = V x A - KP - K1P - K2P - K3P - K4P - K5P, at least 0, V and KP
        being those of the bracket of A, K1P = credit rate x TCP, K3P the
        other provincial credits of the contract. T2 = T4 + V1 + V2 - S -
        P x LCP, at least 0. An exempt contract (claim code E) only bears
        V2. A nil or negative A bears nothing.

        Returns a dictionary with ``basic_tax`` (T4), ``surtax`` (V1),
        ``premium`` (V2), ``reduction`` (S), ``lcp`` (P x LCP) and ``tax``
        (T2).
        """
        result = dict.fromkeys(
            ("basic_tax", "surtax", "premium", "reduction", "lcp", "tax"), 0.0
        )
        if income <= 0:
            return result
        company = vals["company"]
        contract = vals["contract"]
        date = vals["date"]
        premium = self._l10n_ca_prov_premium(vals, prefix, income)
        result.update({"premium": premium, "tax": premium})
        if contract.l10n_ca_prov_td1_type == "exempt":
            return result
        brackets = company._l10n_ca_param(f"{prefix}.brackets", date)
        constant = float_round(bracket_constant(income, brackets), precision_digits=0)
        credit_rate = self._l10n_ca_prov_credit_rate(vals, prefix)
        k1p = credit_rate * self._l10n_ca_prov_claim(vals, prefix, income)
        credits = (
            k1p
            + k2p
            + contract.l10n_ca_prov_other_credits
            + self._l10n_ca_prov_extra_credits(vals, prefix, income, k1p, k2p)
        )
        basic_tax = max(
            0.0, marginal_rate(income, brackets) * income - constant - credits
        )
        surtax = self._l10n_ca_prov_surtax(vals, prefix, basic_tax)
        reduction = self._l10n_ca_prov_reduction(
            vals, prefix, income, basic_tax + surtax
        )
        lcp = self._l10n_ca_prov_lcp(vals, prefix)
        result.update(
            {
                "basic_tax": basic_tax,
                "surtax": surtax,
                "reduction": reduction,
                "lcp": lcp,
                "tax": max(0.0, basic_tax + surtax + premium - reduction - lcp),
            }
        )
        return result

    def _l10n_ca_provincial_tax(self, vals):
        """Provincial income tax of the period, T4127 option 1.

        Regular pay: A is the federal annual taxable income, T2 of A per
        ``_l10n_ca_prov_annual_tax`` with K2P = K2 of the regular
        contributions at the credit rate of the province; tax per period =
        (T1 + T2) / P rounded once, less the federal tax of the period
        (``_l10n_ca_provincial_regular_tax``), plus the additional
        provincial tax of the contract. Non-periodic payments add
        ``_l10n_ca_prov_bonus_tax``. A pay of a year without a version of
        ``<prefix>.bpa`` warns that it uses the amounts of an earlier year.
        """
        prefix = self._l10n_ca_province_prefix(vals["province"])
        if not prefix:
            return super()._l10n_ca_provincial_tax(vals)
        self._l10n_ca_check_indexation(vals, f"{prefix}.bpa")
        contract = vals["contract"]
        annual = vals["federal_annual_income"]
        nonperiodic = vals["nonperiodic"]
        regular = vals
        if nonperiodic:
            regular = self._l10n_ca_regular_values(vals, vals["gross"] - nonperiodic)
        credit_rate = self._l10n_ca_prov_credit_rate(vals, prefix)
        annual_tax = self._l10n_ca_prov_annual_tax(
            vals, prefix, annual, self._l10n_ca_federal_k2(regular, credit_rate)
        )
        vals.update(
            {
                "provincial_annual_income": annual,
                "provincial_basic_tax": annual_tax["basic_tax"],
                "provincial_surtax": annual_tax["surtax"],
                "provincial_premium": annual_tax["premium"],
                "provincial_reduction": annual_tax["reduction"],
                "provincial_lcp": annual_tax["lcp"],
                "provincial_annual_tax": annual_tax["tax"],
                "provincial_regular_tax": self._l10n_ca_provincial_regular_tax(
                    vals, annual_tax["tax"]
                ),
                "provincial_bonus_tax": 0.0,
            }
        )
        if nonperiodic:
            self._l10n_ca_prov_bonus_tax(vals, prefix, regular, credit_rate)
        return (
            vals["provincial_regular_tax"]
            + vals["provincial_bonus_tax"]
            + _round(contract.l10n_ca_prov_additional_tax)
        )

    def _l10n_ca_prov_bonus_tax(self, vals, prefix, regular, credit_rate):
        """TB, the provincial tax on the non-periodic payments of the pay.

        Regular bonus calculation of T4127: T2 of A with the payment
        payable now less T2 of A without it, each T2 recomputed in full. A
        with the payment is the one of the federal step
        (``federal_bonus_income``); A without it is P x (I - F - F2 - F5A -
        U1) of the federal step (``federal_bonus_base``) plus B1 - F5BYTD of
        the year. A pay without regular remuneration thus takes I, F, F2, U1
        and F5A of the most recent regular pay, as the federal step does.
        K2P adds the contributions on the payment once, as the federal K2.
        When A with the payment is at most
        ``l10n_ca.federal.bonus_flat_threshold``, the federal flat rate is
        the whole federal and provincial withholding on the payment (T4127,
        15% outside Quebec) and the federal step withholds it: TB is 0.
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
            tax_with = self._l10n_ca_prov_annual_tax(
                vals,
                prefix,
                with_payment,
                self._l10n_ca_federal_k2(vals, credit_rate, regular),
            )["tax"]
            tax_without = self._l10n_ca_prov_annual_tax(
                vals, prefix, without, self._l10n_ca_federal_k2(regular, credit_rate)
            )["tax"]
            tax = max(0.0, tax_with - tax_without)
        vals.update(
            {
                "provincial_bonus_income": with_payment,
                "provincial_bonus_tax": _round(tax),
            }
        )
        return vals

    # ------------------------------------------------------------------
    # Employer contributions
    # ------------------------------------------------------------------

    def _l10n_ca_prov_previous_domain(self, date):
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

    def _l10n_ca_line_total(self, slip_domain, code):
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

    def _l10n_ca_prov_account(self, vals):
        """Return the provincial payroll account of the company, if any."""
        return self.env["l10n_ca.payroll.province.account"].search(
            [
                ("company_id", "=", vals["company"].id),
                ("province_id", "=", vals["province"].id),
            ],
            limit=1,
        )

    def _l10n_ca_compute_other_contributions(self, vals):
        """Employer payroll tax and workers' compensation premium of a pay.

        For a province registered with this engine. Employer tax = rate x
        (max(0, R + G - E) - max(0, R - E)): G is the gross of the pay, R
        the remuneration in the province that the company paid before it
        this year (rule ``remuneration`` of ``_l10n_ca_prov_rule_codes``),
        E the exemption and the rate the one of the annual total
        remuneration of the rate basis of the company
        (``l10n_ca.payroll.province.account``). The exemption is thus
        consumed by the first pays of the year, and the pays after it bear
        the tax on their whole remuneration. G keeps its sign: a pay of
        negative earnings lowers R and reverses the tax of the part of the
        remuneration above E it takes back.

        Premium = rate per $100 x IE / 100, IE = min(G, maximum - IE of the
        year so far) the insurable earnings of the pay, at least 0, and 0
        for a contract not covered.

        A credit note (``credit_note``) takes its gross out of the year:
        its lines count negatively in R and in the year-to-date amounts, so
        its amounts are those that reverse the pay, positive. Tax = rate x
        (max(0, R - E) - max(0, R - G - E)), the tax of the last G of R.
        IE = min(G, IE of the year so far - min(maximum, S - G)), at least
        0, S being the remuneration of the employee so far: the insurable
        earnings of the year fall to those of the remuneration left.

        A province without ``<prefix>.employer_tax.rates`` has no employer
        tax, one without ``<prefix>.wcb.max_insurable`` no premium. A rate
        basis left at 0 gives the rate and the exemption of a nil
        remuneration, which the payslip warns about.
        """
        vals = super()._l10n_ca_compute_other_contributions(vals)
        province = vals["province"]
        prefix = self._l10n_ca_province_prefix(province)
        if not prefix:
            # The rules of a province module read these keys whether or not
            # its province is registered.
            for key in (
                "province_remuneration",
                "employer_tax",
                "wcb_insurable",
                "wcb",
            ):
                vals.setdefault(key, 0.0)
            return vals
        company = vals["company"]
        contract = vals["contract"]
        date = vals["date"]
        gross = vals["gross"]
        refund = self.credit_note
        account = self._l10n_ca_prov_account(vals)
        codes = self._l10n_ca_prov_rule_codes(province)
        employee_domain = [
            ("employee_id", "=", self.employee_id.id),
            *self._l10n_ca_prov_previous_domain(date),
        ]
        result = {
            "province_remuneration": gross,
            "employer_tax": 0.0,
            "employer_tax_rate": 0.0,
            "employer_tax_line_name": self._l10n_ca_employer_tax_name(province),
            "wcb_insurable": 0.0,
            "wcb": 0.0,
            "wcb_line_name": self._l10n_ca_wcb_name(province),
        }
        if self._l10n_ca_prov_param(vals, prefix, "employer_tax.rates"):
            total_payroll = account._l10n_ca_employer_tax_payroll()
            if total_payroll <= 0:
                self._l10n_ca_warn_employer_tax_basis(vals, account)
            rate = account._l10n_ca_employer_tax_rate(
                company, prefix, total_payroll, date
            )
            exemption = account._l10n_ca_employer_tax_exemption(
                company, prefix, total_payroll, date
            )
            paid = self._l10n_ca_line_total(
                self._l10n_ca_prov_previous_domain(date), codes["remuneration"]
            )
            if refund:
                taxable = max(0.0, paid - exemption) - max(
                    0.0, paid - gross - exemption
                )
            else:
                taxable = max(0.0, paid + gross - exemption) - max(
                    0.0, paid - exemption
                )
            result.update(
                {
                    "employer_tax_payroll": total_payroll,
                    "employer_tax_rate": rate,
                    "employer_tax_exemption": exemption,
                    "employer_tax_paid": paid,
                    "employer_tax_taxable": taxable,
                    "employer_tax": _round(rate * taxable),
                    "employer_tax_line_name": _(
                        "%(name)s (%(rate)s%%)",
                        name=self._l10n_ca_employer_tax_name(province),
                        rate=formatLang(self.env, rate * 100, digits=3),
                    ),
                }
            )
        maximum = self._l10n_ca_prov_param(vals, prefix, "wcb.max_insurable")
        if maximum is not None and not contract.l10n_ca_wcb_exempt:
            insured = self._l10n_ca_line_total(employee_domain, codes["wcb_insurable"])
            if refund:
                salary = self._l10n_ca_line_total(
                    employee_domain, codes["remuneration"]
                )
                left = min(maximum, max(0.0, salary - gross))
                insurable = min(gross, insured - left)
            else:
                insurable = min(gross, maximum - insured)
            insurable = max(0.0, insurable)
            result.update(
                {
                    "wcb_insurable": insurable,
                    "wcb": _round(insurable * account.wcb_rate / 100),
                }
            )
        vals.update(result)
        return vals

    def _l10n_ca_warn_employer_tax_basis(self, vals, account):
        """Add to ``vals["warnings"]`` that the rate basis of the employer
        tax is 0, naming the province and the menu of the accounts."""
        message = _(
            "The total remuneration of %(company)s in %(province)s that sets the "
            "employer payroll tax is 0 (Payroll > Configuration > Provincial "
            "Payroll Accounts): this payslip uses the lowest rate and the "
            "exemption of a nil remuneration.",
            company=vals["company"].name,
            province=vals["province"].name,
        )
        if message not in vals["warnings"]:
            vals["warnings"].append(message)
