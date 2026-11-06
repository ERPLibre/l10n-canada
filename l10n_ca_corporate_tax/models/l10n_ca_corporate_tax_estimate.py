# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo import _, api, fields, models

from ..tools import add_months, linear_ratio

PL_ACCOUNT_TYPES = (
    "income",
    "income_other",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
)

RESULT_FIELDS = (
    "taxable_income",
    "investment_income_used",
    "psb_income_used",
    "active_income",
    "business_limit",
    "business_limit_reduction",
    "reduced_business_limit",
    "sbd_income",
    "fed_base_tax",
    "fed_abatement",
    "fed_sbd",
    "fed_full_rate_income",
    "fed_general_reduction",
    "fed_refundable_tax",
    "fed_psb_tax",
    "federal_tax",
    "nerdtoh_addition",
    "non_eligible_dividends_paid",
    "dividend_refund",
    "qc_general_tax",
    "qc_sbd_rate",
    "qc_sbd_factor",
    "qc_business_limit",
    "qc_sbd",
    "quebec_tax",
    "total_tax",
)


class L10nCaCorporateTaxEstimate(models.Model):
    _name = "l10n.ca.corporate.tax.estimate"
    _description = "Corporate Income Tax Estimate"
    _inherit = ["mail.thread"]
    _order = "date_to desc"

    @api.model
    def _default_dates(self):
        company = self.env.company
        return company._l10n_ca_fiscal_year(fields.Date.context_today(self))

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    ccpc = fields.Boolean(related="company_id.l10n_ca_ccpc", string="CCPC")
    date_from = fields.Date(
        string="Fiscal Year Start",
        required=True,
        default=lambda self: self._default_dates()[0],
    )
    date_to = fields.Date(
        string="Fiscal Year End",
        required=True,
        default=lambda self: self._default_dates()[1],
    )
    # ---- Inputs
    accounting_income = fields.Monetary(
        string="Accounting Income Before Taxes",
        tracking=True,
        help="Net income of the profit and loss accounts for the fiscal "
        "year, loaded from the posted entries.",
    )
    adjustment_ids = fields.One2many(
        "l10n.ca.corporate.tax.adjustment", "estimate_id", string="Adjustments"
    )
    loss_carryforward = fields.Monetary(
        string="Non-Capital Losses Applied",
        help="Losses of other years deducted in computing taxable income.",
    )
    investment_income = fields.Monetary(
        string="Aggregate Investment Income",
        help="Income from property (interest, rents, taxable capital "
        "gains, ...) included in taxable income; it gets no small business "
        "deduction and bears the refundable tax.",
    )
    psb_income = fields.Monetary(
        string="Personal Services Business Income",
        help="Income of an incorporated employee: no small business "
        "deduction nor general rate reduction, and an additional federal "
        "tax.",
    )
    business_limit_allocation = fields.Float(
        string="Business Limit Allocated (%)",
        default=100.0,
        help="Share of the business limit allocated to the company when it "
        "is associated with other corporations (schedule 23 / CO-771.1.3).",
    )
    taxable_capital = fields.Monetary(
        string="Taxable Capital of the Preceding Year",
        help="Taxable capital employed in Canada of the company and its "
        "associated corporations for the preceding year.",
    )
    previous_aaii = fields.Monetary(
        string="Adjusted Aggregate Investment Income of the Preceding Year",
        help="Of the company and its associated corporations: above the "
        "threshold, it reduces the business limit.",
    )
    previous_taxable_income = fields.Monetary(
        string="Taxable Income of the Preceding Year",
        help="Of the company and its associated corporations; decides the "
        "three-month balance-due delay and the quarterly instalments.",
    )
    previous_sbd_claimed = fields.Boolean(
        string="SBD Claimed in the Preceding Year",
    )
    group_taxable_income = fields.Monetary(
        string="Taxable Income of the Associated Group",
        help="Taxable income of the year of the company and its associated "
        "corporations, compared with the quarterly instalment maximum. "
        "Below the taxable income of the company, the latter is used.",
    )
    previous_business_income = fields.Boolean(
        string="Business Income in the Preceding Year",
        help="The company had income from a qualifying business carried on "
        "in Canada in the preceding year, a condition of the Quebec "
        "quarterly instalments. The SBD claimed in the preceding year "
        "implies it.",
    )
    qc_paid_up_capital = fields.Monetary(
        string="Quebec Paid-Up Capital of the Year",
        help="Paid-up capital of the company and its associated "
        "corporations for the year. Quebec quarterly instalments require "
        "this amount or the one of the preceding year not to exceed the "
        "maximum.",
    )
    previous_qc_paid_up_capital = fields.Monetary(
        string="Quebec Paid-Up Capital of the Preceding Year",
        help="Paid-up capital of the company and its associated "
        "corporations for the preceding year. For the Quebec business "
        "limit, it is amount J of form CO-771: the paid-up capital of their "
        "last taxation year ended in the preceding calendar year, doubled "
        "for an insurance corporation or a financial institution; left at "
        "zero, the federal taxable capital stands for it in that grind.",
    )
    tax_obligations_met = fields.Boolean(
        string="Tax Obligations Met in the Last 12 Months",
        default=True,
        help="The company filed its returns and paid or remitted the amounts "
        "due over the last 12 months, a condition of the quarterly "
        "instalments federally and in Quebec.",
    )
    previous_federal_tax = fields.Monetary(
        string="Federal Tax of the Preceding Year",
        help="First instalment base: instalments are required only when "
        "both this amount and the tax of the year exceed the threshold.",
    )
    previous_quebec_tax = fields.Monetary(string="Quebec Tax of the Preceding Year")
    instalment_ids = fields.One2many(
        "l10n.ca.corporate.tax.instalment", "estimate_id", string="Instalments"
    )
    note = fields.Text()
    # ---- Results
    paid_hours_id = fields.Many2one(
        "l10n.ca.paid.hours",
        string="Remunerated Hours",
        compute="_compute_tax",
    )
    taxable_income = fields.Monetary(compute="_compute_tax")
    investment_income_used = fields.Monetary(
        string="Investment Income Taxed", compute="_compute_tax"
    )
    psb_income_used = fields.Monetary(string="PSB Income Taxed", compute="_compute_tax")
    active_income = fields.Monetary(
        string="Active Business Income", compute="_compute_tax"
    )
    business_limit = fields.Monetary(compute="_compute_tax")
    business_limit_reduction = fields.Monetary(
        string="Business Limit Grind",
        compute="_compute_tax",
        help="Greater of the taxable capital grind and the passive income "
        "grind (ITA s. 125(5.1)).",
    )
    reduced_business_limit = fields.Monetary(compute="_compute_tax")
    sbd_income = fields.Monetary(
        string="Income Eligible for the SBD", compute="_compute_tax"
    )
    fed_base_tax = fields.Monetary(string="Federal Basic Tax", compute="_compute_tax")
    fed_abatement = fields.Monetary(string="Federal Abatement", compute="_compute_tax")
    fed_sbd = fields.Monetary(
        string="Federal Small Business Deduction", compute="_compute_tax"
    )
    fed_full_rate_income = fields.Monetary(
        string="Full Rate Taxable Income", compute="_compute_tax"
    )
    fed_general_reduction = fields.Monetary(
        string="Federal General Rate Reduction", compute="_compute_tax"
    )
    fed_refundable_tax = fields.Monetary(
        string="Additional Refundable Tax on Investment Income",
        compute="_compute_tax",
    )
    fed_psb_tax = fields.Monetary(
        string="Additional Tax on PSB Income", compute="_compute_tax"
    )
    federal_tax = fields.Monetary(string="Federal Part I Tax", compute="_compute_tax")
    nerdtoh_addition = fields.Monetary(
        string="Refundable Portion of Part I Tax",
        compute="_compute_tax",
        help="Added to the non-eligible refundable dividend tax on hand; "
        "recovered when taxable dividends are paid.",
    )
    non_eligible_dividends_paid = fields.Monetary(
        string="Non-Eligible Dividends Paid in the Year", compute="_compute_tax"
    )
    dividend_refund = fields.Monetary(
        string="Dividend Refund (Estimate)",
        compute="_compute_tax",
        help="Lesser of the refundable portion of the year and the dividend "
        "refund rate times the non-eligible dividends paid in the year. "
        "Opening refundable dividend tax on hand balances are not tracked.",
    )
    qc_general_tax = fields.Monetary(
        string="Quebec Tax at the General Rate", compute="_compute_tax"
    )
    qc_sbd_rate = fields.Float(
        string="Quebec SBD Rate", compute="_compute_tax", digits=(16, 4)
    )
    qc_sbd_factor = fields.Float(
        string="Quebec SBD Factor", compute="_compute_tax", digits=(16, 4)
    )
    qc_business_limit = fields.Monetary(
        string="Quebec Business Limit", compute="_compute_tax"
    )
    qc_sbd = fields.Monetary(
        string="Quebec Small Business Deduction", compute="_compute_tax"
    )
    quebec_tax = fields.Monetary(string="Quebec Income Tax", compute="_compute_tax")
    total_tax = fields.Monetary(
        string="Total Estimated Tax",
        compute="_compute_tax",
        help="Federal Part I tax plus Quebec tax, less the estimated dividend refund.",
    )
    instalment_frequency = fields.Selection(
        [("monthly", "Monthly"), ("quarterly", "Quarterly")],
        string="Federal Instalment Frequency",
        compute="_compute_tax",
    )
    qc_instalment_frequency = fields.Selection(
        [("monthly", "Monthly"), ("quarterly", "Quarterly")],
        string="Quebec Instalment Frequency",
        compute="_compute_tax",
    )
    fed_instalments_required = fields.Boolean(
        string="Federal Instalments Required", compute="_compute_tax"
    )
    qc_instalments_required = fields.Boolean(
        string="Quebec Instalments Required", compute="_compute_tax"
    )
    fed_balance_due_date = fields.Date(
        string="Federal Balance Due", compute="_compute_tax"
    )
    qc_balance_due_date = fields.Date(
        string="Quebec Balance Due", compute="_compute_tax"
    )
    filing_due_date = fields.Date(
        string="T2 and CO-17 Filing Deadline", compute="_compute_tax"
    )
    warning_message = fields.Text(compute="_compute_tax")

    @api.depends("date_to")
    def _compute_name(self):
        for record in self:
            record.name = _("Estimate %s", record.date_to or "")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _p(self, code):
        """Return parameter ``code`` at the first day of the fiscal year."""
        return self.company_id._l10n_ca_param(code, self.date_from)

    def _l10n_ca_paid_hours_record(self):
        self.ensure_one()
        return self.env["l10n.ca.paid.hours"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_from", "=", self.date_from),
            ],
            limit=1,
        )

    def _l10n_ca_non_eligible_dividends(self):
        self.ensure_one()
        dividends = self.env["l10n.ca.dividend"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "paid"),
                ("dividend_type", "=", "non_eligible"),
                ("payment_date", ">=", self.date_from),
                ("payment_date", "<=", self.date_to),
            ]
        )
        return sum(dividends.mapped("amount"))

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    @api.depends(
        "company_id",
        "date_from",
        "date_to",
        "accounting_income",
        "adjustment_ids.amount",
        "loss_carryforward",
        "investment_income",
        "psb_income",
        "business_limit_allocation",
        "taxable_capital",
        "previous_aaii",
        "previous_taxable_income",
        "previous_sbd_claimed",
        "group_taxable_income",
        "previous_business_income",
        "qc_paid_up_capital",
        "previous_qc_paid_up_capital",
        "tax_obligations_met",
        "company_id.l10n_ca_instalment_frequency",
        "company_id.l10n_ca_qc_instalment_frequency",
        "previous_federal_tax",
        "previous_quebec_tax",
    )
    def _compute_tax(self):
        for record in self:
            if not (record.company_id and record.date_from and record.date_to):
                record.update({name: 0.0 for name in RESULT_FIELDS})
                record.update(
                    {
                        "paid_hours_id": False,
                        "instalment_frequency": False,
                        "qc_instalment_frequency": False,
                        "fed_instalments_required": False,
                        "qc_instalments_required": False,
                        "fed_balance_due_date": False,
                        "qc_balance_due_date": False,
                        "filing_due_date": False,
                        "warning_message": False,
                    }
                )
                continue
            record.update(record._l10n_ca_compute_values())

    def _l10n_ca_short_year_ratio(self, weeks_code):
        """Return the proration of a business limit for the fiscal year.

        ``days / 365`` when the year has fewer weeks than parameter
        ``weeks_code``, else 1; the days never count for more than 365.
        """
        self.ensure_one()
        days = (self.date_to - self.date_from).days + 1
        if days < self._p(weeks_code) * 7:
            return min(days, 365) / 365.0
        return 1.0

    def _l10n_ca_ground_limit(self, base_limit, weeks_code, capital, lower, upper):
        """Return ``(limit, reduction, reduced)`` of a business limit.

        ``base_limit`` is allocated, prorated for a short year, then reduced
        by the greater of the capital grind (``capital`` linear between the
        ``lower`` and ``upper`` parameters) and the passive income grind
        (adjusted aggregate investment income of the preceding year above
        the threshold), never below nil.
        """
        self.ensure_one()
        limit = (
            base_limit
            * self.business_limit_allocation
            / 100.0
            * self._l10n_ca_short_year_ratio(weeks_code)
        )
        capital_reduction = limit * linear_ratio(
            capital, self._p(lower), self._p(upper)
        )
        passive_excess = max(
            0.0,
            self.previous_aaii - self._p("l10n_ca.corp_tax.fed.aaii_grind_threshold"),
        )
        passive_reduction = (
            limit
            * self._p("l10n_ca.corp_tax.fed.aaii_grind_multiplier")
            * passive_excess
            / base_limit
            if base_limit
            else 0.0
        )
        reduction = min(limit, max(capital_reduction, passive_reduction))
        return limit, reduction, limit - reduction

    def _l10n_ca_business_limit(self):
        """Return ``(limit, reduction, reduced)`` of the federal business limit.

        The capital grind reads the taxable capital employed in Canada (ITA
        s. 125(5.1)(a)).
        """
        self.ensure_one()
        return self._l10n_ca_ground_limit(
            self._p("l10n_ca.corp_tax.fed.business_limit"),
            "l10n_ca.corp_tax.fed.short_year_weeks",
            self.taxable_capital,
            "l10n_ca.corp_tax.fed.tc_grind_lower",
            "l10n_ca.corp_tax.fed.tc_grind_upper",
        )

    def _l10n_ca_qc_business_limit(self):
        """Return ``(limit, reduction, reduced)`` of the Quebec business limit.

        Form CO-771, part 8.1: the limit prorated for a short year (line
        80), less the greater of the paid-up capital grind (lines 84 to 95,
        on amount J, the paid-up capital of the preceding year) and the
        passive income grind. The paid-up capital falls back on the federal
        taxable capital when it is not entered.
        """
        self.ensure_one()
        return self._l10n_ca_ground_limit(
            self._p("l10n_ca.corp_tax.qc.business_limit"),
            "l10n_ca.corp_tax.qc.short_year_weeks",
            self.previous_qc_paid_up_capital or self.taxable_capital,
            "l10n_ca.corp_tax.qc.pc_grind_lower",
            "l10n_ca.corp_tax.qc.pc_grind_upper",
        )

    def _l10n_ca_compute_values(self):
        """Return the values of every result field of the estimate.

        All the rates are read at the first day of the fiscal year: a rate
        that changes during the year applies to the next year only.
        """
        self.ensure_one()
        currency = self.currency_id
        warnings = [
            _(
                "This is an estimate for planning purposes, not a tax return. "
                "File the T2 and CO-17 returns with certified software."
            )
        ]
        ccpc = self.company_id.l10n_ca_ccpc
        taxable = max(
            0.0,
            self.accounting_income
            + sum(self.adjustment_ids.mapped("amount"))
            - self.loss_carryforward,
        )
        investment = min(max(0.0, self.investment_income), taxable)
        psb = min(max(0.0, self.psb_income), taxable - investment)
        active = taxable - investment - psb

        limit, reduction, reduced = self._l10n_ca_business_limit()
        sbd_income = min(active, reduced) if ccpc else 0.0

        # Federal Part I tax (ITA s. 123 to 125)
        fed_base = taxable * self._p("l10n_ca.corp_tax.fed.base_rate")
        fed_abatement = taxable * self._p("l10n_ca.corp_tax.fed.abatement_rate")
        fed_sbd = sbd_income * self._p("l10n_ca.corp_tax.fed.sbd_rate")
        full_rate_income = max(
            0.0, taxable - sbd_income - (investment if ccpc else 0.0) - psb
        )
        fed_grr = full_rate_income * self._p(
            "l10n_ca.corp_tax.fed.general_reduction_rate"
        )
        refundable_base = min(investment, taxable - sbd_income) if ccpc else 0.0
        fed_art = refundable_base * self._p("l10n_ca.corp_tax.fed.art_rate")
        fed_psb = psb * self._p("l10n_ca.corp_tax.fed.psb_additional_rate")
        federal_tax = fed_base - fed_abatement - fed_sbd - fed_grr + fed_art + fed_psb
        nerdtoh = refundable_base * self._p("l10n_ca.corp_tax.fed.nerdtoh_rate")
        non_eligible_paid = self._l10n_ca_non_eligible_dividends()
        dividend_refund = min(
            nerdtoh,
            non_eligible_paid * self._p("l10n_ca.corp_tax.fed.dividend_refund_rate"),
        )

        # Quebec income tax (Taxation Act s. 771 and following)
        qc_general = taxable * self._p("l10n_ca.corp_tax.qc.general_rate")
        qc_rate = self._p("l10n_ca.corp_tax.qc.sbd_rate")
        paid_hours = self._l10n_ca_paid_hours_record()
        qc_factor = paid_hours.sbd_factor if paid_hours else 0.0
        if ccpc and not paid_hours:
            warnings.append(
                _(
                    "No remunerated hours record for this fiscal year: the "
                    "Quebec small business deduction is estimated at nil."
                )
            )
        qc_limit = self._l10n_ca_qc_business_limit()[2]
        qc_sbd = min(active, qc_limit) * qc_rate * qc_factor if ccpc else 0.0
        quebec_tax = qc_general - qc_sbd

        # Instalments (ITA s. 157; Taxation Act s. 1027). Monthly is the
        # rule; quarterly is open when every condition of the jurisdiction
        # holds. The taxable income counts the associated corporations.
        group_taxable = max(taxable, self.group_taxable_income)
        fed_max = self._p("l10n_ca.corp_tax.fed.quarterly_taxable_income_max")
        fed_quarterly_ok = (
            ccpc
            and self.tax_obligations_met
            and (group_taxable <= fed_max or self.previous_taxable_income <= fed_max)
            and self.taxable_capital
            <= self._p("l10n_ca.corp_tax.fed.quarterly_taxable_capital_max")
            and (sbd_income > 0 or self.previous_sbd_claimed)
        )
        # Quebec (guide CO-17.G, section 3.9.3): income from a qualifying
        # business, whether or not a business limit is left for the SBD,
        # and the paid-up capital of the year or of the preceding year.
        qc_max = self._p("l10n_ca.corp_tax.qc.quarterly_taxable_income_max")
        qc_capital_max = self._p("l10n_ca.corp_tax.qc.quarterly_paid_up_capital_max")
        qc_quarterly_ok = (
            ccpc
            and self.tax_obligations_met
            and (group_taxable <= qc_max or self.previous_taxable_income <= qc_max)
            and (
                active > 0 or self.previous_business_income or self.previous_sbd_claimed
            )
            and (
                self.qc_paid_up_capital <= qc_capital_max
                or self.previous_qc_paid_up_capital <= qc_capital_max
            )
        )
        # An empty Quebec profile follows the federal one.
        fed_profile = self.company_id.l10n_ca_instalment_frequency
        qc_profile = self.company_id.l10n_ca_qc_instalment_frequency or fed_profile
        frequency = (
            "quarterly" if fed_quarterly_ok and fed_profile != "monthly" else "monthly"
        )
        qc_frequency = (
            "quarterly" if qc_quarterly_ok and qc_profile != "monthly" else "monthly"
        )
        if fed_profile == "quarterly" and not fed_quarterly_ok:
            warnings.append(
                _(
                    "The company profile says quarterly instalments, but the "
                    "small-CCPC conditions are not met: monthly instalments "
                    "are estimated."
                )
            )
        if qc_profile == "quarterly" and not qc_quarterly_ok:
            warnings.append(
                _(
                    "The company profile says quarterly Quebec instalments, but "
                    "the Quebec conditions are not met: monthly Quebec "
                    "instalments are estimated."
                )
            )
        fed_threshold = self._p("l10n_ca.corp_tax.fed.instalment_threshold")
        qc_threshold = self._p("l10n_ca.corp_tax.qc.instalment_threshold")
        fed_required = (
            federal_tax > fed_threshold and self.previous_federal_tax > fed_threshold
        )
        qc_required = (
            quebec_tax > qc_threshold and self.previous_quebec_tax > qc_threshold
        )
        if (fed_profile == "none" and fed_required) or (
            qc_profile == "none" and qc_required
        ):
            warnings.append(
                _("Instalments are required although the company profile says none.")
            )

        # Balance-due and filing dates. ITA s. 248(1) balance-due day
        # (d)(i): SBD claimed in the year or the preceding year, and
        # taxable income of the preceding year within the business limit;
        # the reduced limit of the year stands for the preceding one.
        small_ccpc = (
            ccpc
            and (sbd_income > 0 or self.previous_sbd_claimed)
            and self.previous_taxable_income <= reduced
        )
        fed_months = self._p(
            "l10n_ca.corp_tax.fed.balance_due_months_ccpc"
            if small_ccpc
            else "l10n_ca.corp_tax.fed.balance_due_months"
        )
        qc_months = self._p(
            "l10n_ca.corp_tax.qc.balance_due_months_ccpc"
            if small_ccpc
            else "l10n_ca.corp_tax.qc.balance_due_months"
        )
        filing_months = self._p("l10n_ca.corp_tax.filing_months")

        rnd = currency.round
        return {
            "paid_hours_id": paid_hours,
            "taxable_income": rnd(taxable),
            "investment_income_used": rnd(investment),
            "psb_income_used": rnd(psb),
            "active_income": rnd(active),
            "business_limit": rnd(limit),
            "business_limit_reduction": rnd(reduction),
            "reduced_business_limit": rnd(reduced),
            "sbd_income": rnd(sbd_income),
            "fed_base_tax": rnd(fed_base),
            "fed_abatement": rnd(fed_abatement),
            "fed_sbd": rnd(fed_sbd),
            "fed_full_rate_income": rnd(full_rate_income),
            "fed_general_reduction": rnd(fed_grr),
            "fed_refundable_tax": rnd(fed_art),
            "fed_psb_tax": rnd(fed_psb),
            "federal_tax": rnd(federal_tax),
            "nerdtoh_addition": rnd(nerdtoh),
            "non_eligible_dividends_paid": rnd(non_eligible_paid),
            "dividend_refund": rnd(dividend_refund),
            "qc_general_tax": rnd(qc_general),
            "qc_sbd_rate": qc_rate,
            "qc_sbd_factor": qc_factor,
            "qc_business_limit": rnd(qc_limit),
            "qc_sbd": rnd(qc_sbd),
            "quebec_tax": rnd(quebec_tax),
            "total_tax": rnd(federal_tax + quebec_tax - dividend_refund),
            "instalment_frequency": frequency,
            "qc_instalment_frequency": qc_frequency,
            "fed_instalments_required": fed_required,
            "qc_instalments_required": qc_required,
            "fed_balance_due_date": add_months(self.date_to, int(fed_months)),
            "qc_balance_due_date": add_months(self.date_to, int(qc_months)),
            "filing_due_date": add_months(self.date_to, int(filing_months)),
            "warning_message": "\n".join(warnings),
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _l10n_ca_account_balances(self):
        """Return ``{account: balance}`` of the P&L accounts for the year."""
        self.ensure_one()
        groups = self.env["account.move.line"]._read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("parent_state", "=", "posted"),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("account_id.account_type", "in", PL_ACCOUNT_TYPES),
            ],
            ["account_id"],
            ["balance:sum"],
        )
        return dict(groups)

    def _l10n_ca_get_cca_adjustments(self):
        """Return the capital cost allowance lines of the fiscal year.

        Hook for a capital cost allowance module: a list of dicts with
        ``name`` and ``amount`` (negative: a deduction). The base version
        returns none; the CCA is then entered as a manual line.
        """
        self.ensure_one()
        return []

    def _l10n_ca_accounting_adjustments(self, balances):
        """Return the automatic adjustment values from account balances."""
        self.ensure_one()
        meals = sum(
            b for a, b in balances.items() if a.l10n_ca_tax_treatment == "meals"
        )
        non_deductible = sum(
            b
            for a, b in balances.items()
            if a.l10n_ca_tax_treatment == "non_deductible"
        )
        depreciation = sum(
            b for a, b in balances.items() if a.account_type == "expense_depreciation"
        )
        deductible_rate = self._p("l10n_ca.corp_tax.meals_deductible_rate")
        values = []
        if meals:
            values.append(
                {
                    "adjustment_type": "meals",
                    "name": _("Non-deductible meals and entertainment"),
                    "amount": meals * (1.0 - deductible_rate),
                }
            )
        if non_deductible:
            values.append(
                {
                    "adjustment_type": "non_deductible",
                    "name": _("Non-deductible expenses"),
                    "amount": non_deductible,
                }
            )
        if depreciation:
            values.append(
                {
                    "adjustment_type": "depreciation",
                    "name": _("Book depreciation added back"),
                    "amount": depreciation,
                }
            )
        for cca in self._l10n_ca_get_cca_adjustments():
            values.append(dict(cca, adjustment_type="cca"))
        return values

    def action_load_accounting(self):
        """Load accounting income and automatic adjustments from the books.

        Replaces the automatic adjustment lines; manual lines stay.
        """
        for record in self:
            balances = record._l10n_ca_account_balances()
            investment = -sum(
                b
                for a, b in balances.items()
                if a.l10n_ca_tax_treatment == "investment"
            )
            record.adjustment_ids.filtered("auto").unlink()
            record.write(
                {
                    "accounting_income": -sum(balances.values()),
                    "investment_income": max(0.0, investment),
                    "adjustment_ids": [
                        fields.Command.create(dict(values, auto=True))
                        for values in record._l10n_ca_accounting_adjustments(balances)
                    ],
                }
            )
        return True

    def _l10n_ca_instalment_dates(self, frequency):
        self.ensure_one()
        step = 3 if frequency == "quarterly" else 1
        start = self.date_from - datetime.timedelta(days=1)
        dates = []
        months = step
        while True:
            day = add_months(start, months)
            if day > self.date_to:
                break
            dates.append(day)
            months += step
        return dates or [self.date_to]

    def action_compute_instalments(self):
        """Rebuild the instalment schedule of both jurisdictions.

        Each jurisdiction follows its own frequency. Each instalment is the
        lesser of the tax of the year and the tax of the preceding year,
        divided by the number of instalments; the last one absorbs the
        rounding.
        """
        for record in self:
            record.instalment_ids.unlink()
            commands = []
            for jurisdiction, required, frequency, current, previous in (
                (
                    "federal",
                    record.fed_instalments_required,
                    record.instalment_frequency,
                    record.federal_tax,
                    record.previous_federal_tax,
                ),
                (
                    "quebec",
                    record.qc_instalments_required,
                    record.qc_instalment_frequency,
                    record.quebec_tax,
                    record.previous_quebec_tax,
                ),
            ):
                if not required:
                    continue
                dates = record._l10n_ca_instalment_dates(frequency)
                base = min(current, previous)
                amount = record.currency_id.round(base / len(dates))
                for index, day in enumerate(dates):
                    if index == len(dates) - 1:
                        amount = record.currency_id.round(
                            base - amount * (len(dates) - 1)
                        )
                    commands.append(
                        fields.Command.create(
                            {
                                "jurisdiction": jurisdiction,
                                "date": day,
                                "amount": amount,
                            }
                        )
                    )
            record.write({"instalment_ids": commands})
        return True


class L10nCaCorporateTaxAdjustment(models.Model):
    _name = "l10n.ca.corporate.tax.adjustment"
    _description = "Corporate Tax Estimate Adjustment"
    _order = "estimate_id, sequence, id"

    estimate_id = fields.Many2one(
        "l10n.ca.corporate.tax.estimate", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="estimate_id.company_id", store=True)
    currency_id = fields.Many2one(related="estimate_id.currency_id")
    sequence = fields.Integer(default=10)
    adjustment_type = fields.Selection(
        [
            ("meals", "Meals and entertainment"),
            ("depreciation", "Book depreciation"),
            ("cca", "Capital cost allowance"),
            ("non_deductible", "Non-deductible expense"),
            ("other", "Other"),
        ],
        string="Type",
        required=True,
        default="other",
    )
    name = fields.Char(string="Description", required=True)
    amount = fields.Monetary(
        help="Positive: added to accounting income. Negative: deducted."
    )
    auto = fields.Boolean(
        string="Automatic",
        readonly=True,
        help="Created from the books; replaced at the next load.",
    )


class L10nCaCorporateTaxInstalment(models.Model):
    _name = "l10n.ca.corporate.tax.instalment"
    _description = "Corporate Tax Instalment"
    _order = "date, jurisdiction"

    estimate_id = fields.Many2one(
        "l10n.ca.corporate.tax.estimate", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="estimate_id.company_id", store=True)
    currency_id = fields.Many2one(related="estimate_id.currency_id")
    jurisdiction = fields.Selection(
        [("federal", "Federal (CRA)"), ("quebec", "Quebec (Revenu Quebec)")],
        required=True,
    )
    date = fields.Date(string="Due Date", required=True)
    amount = fields.Monetary()
