# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re
from collections import defaultdict
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools.misc import formatLang
from odoo.tools.safe_eval import safe_eval

# Structure of each return: the l10n_ca report it evaluates and the report
# line codes that play a role in the net tax, the closing and the quick
# method. These are form line codes of the core report data, not amounts.
# Each "family" is one tax of the return, read in one expression label.
# Under the quick method, "supplies_line" (line 101) is the tax-included
# eligible supplies of the family when "supplies_tax" is None, and else the
# regular line 101 plus the regular value of "supplies_tax": the FPZ-500
# reports its line 101 including the GST/HST, but not the QST.
KIND_SPECS = {
    "gst_hst": {
        "report": "l10n_ca.l10n_ca_tr_gsthst",
        "frequency_field": "l10n_ca_gst_filing_frequency",
        "authority_field": "l10n_ca_gst_authority_account_id",
        "net_tax": [("Ca109", "balance")],
        "amount_due": [("Ca113C", "balance")],
        "quick_hidden": ("Ca90", "Ca91"),
        "supplies_line": ("Ca101", "balance"),
        "supplies_tax": None,
        "families": [
            {
                "tax": "gst",
                "label": "balance",
                "collected_line": "Ca103",
                "collected_tag": "Ca103",
                "itc_line": "Ca106",
                "itc_tag": "Ca106",
                "deducted_line": "Ca107",
            },
        ],
    },
    "qst": {
        "report": "l10n_ca.l10n_ca_tr_qst",
        "frequency_field": "l10n_ca_qst_filing_frequency",
        "authority_field": "l10n_ca_qst_authority_account_id",
        "net_tax": [("CaQc109209", "gsthst"), ("CaQc109209", "qst")],
        "amount_due": [("CaQc116216", "gsthst"), ("CaQc116216", "qst")],
        "quick_hidden": (),
        "supplies_line": ("CaQc101", "gsthst"),
        "supplies_tax": ("CaQc103203", "gsthst"),
        "families": [
            {
                "tax": "gst",
                "label": "gsthst",
                "collected_line": "CaQc103203",
                "collected_tag": "CaQc103",
                "itc_line": "CaQc106206",
                "itc_tag": "CaQc106",
                "deducted_line": "CaQc107207",
            },
            {
                "tax": "qst",
                "label": "qst",
                "collected_line": "CaQc103203",
                "collected_tag": "CaQc203",
                "itc_line": "CaQc106206",
                "itc_tag": "CaQc206",
                "deducted_line": "CaQc107207",
            },
        ],
    },
}

# Account types of capital property, real property included. Under the
# quick method, only the input tax credits of purchases on these accounts
# are claimed, and sales on these accounts are not eligible supplies.
CAPITAL_ACCOUNT_TYPES = ("asset_fixed", "asset_non_current")

_TERM_RE = re.compile(r"\b([A-Za-z_][\w]*)\.([A-Za-z_]\w*)\b")
_BOUND_RE = re.compile(r"[A-Z]{3}\((-?[\d.]+)\)")
_FORM_NUMBER_RE = re.compile(r"^\s*((?:\d+[A-Z]?\s*-\s*)+)(.*)$")


class L10nCaTaxReturn(models.Model):
    _name = "l10n.ca.tax.return"
    _description = "Canadian Sales Tax Return"
    _inherit = "mail.thread"
    _order = "date_to desc, kind, id desc"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    kind = fields.Selection(
        [
            ("gst_hst", "GST/HST (GST34)"),
            ("qst", "Quebec GST/HST and QST (FPZ-500)"),
        ],
        required=True,
        default=lambda self: self._default_kind(),
        tracking=True,
    )
    date_range_id = fields.Many2one(
        "date.range",
        string="Period",
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    date_from = fields.Date(required=True, tracking=True)
    date_to = fields.Date(required=True, tracking=True)
    date_due = fields.Date(
        string="Due Date",
        compute="_compute_date_due",
        store=True,
        help="Last day to file the return and remit the net tax.",
    )
    method = fields.Selection(
        [("regular", "Regular"), ("quick", "Quick method")],
        required=True,
        default=lambda self: self._default_method(),
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("computed", "Computed"),
            ("closed", "Closed"),
            ("filed", "Filed"),
        ],
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )
    line_ids = fields.One2many(
        "l10n.ca.tax.return.line", "return_id", string="Lines", copy=False
    )
    net_tax = fields.Monetary(
        readonly=True,
        copy=False,
        help="Net tax of the return (line 109, or 109 + 209): positive when "
        "tax is owed to the authority.",
    )
    regular_net_tax = fields.Monetary(
        string="Net Tax in the Books",
        readonly=True,
        copy=False,
        help="Net tax under the regular method, which is the balance the "
        "closing entry moves out of the tax accounts.",
    )
    quick_method_gain = fields.Monetary(
        compute="_compute_quick_method_gain",
        help="Tax recorded in the books minus tax remitted under the quick method.",
    )
    amount_due = fields.Monetary(
        readonly=True,
        copy=False,
        help="Balance after credits and debits (line 113C, or 116 + 216): "
        "positive when payable, negative when a refund is claimed.",
    )
    quick_method_note = fields.Text(readonly=True, copy=False)
    filing_date = fields.Date(copy=False, tracking=True)
    confirmation_number = fields.Char(copy=False, tracking=True)
    closing_move_id = fields.Many2one(
        "account.move", string="Closing Entry", readonly=True, copy=False
    )
    note = fields.Html()

    @api.model
    def _default_kind(self):
        state = self.env.company.state_id
        return "qst" if state and state.code == "QC" else "gst_hst"

    @api.model
    def _default_method(self):
        return "quick" if self.env.company.l10n_ca_quick_method else "regular"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "date_from" in fields_list and not res.get("date_from"):
            company = self.env["res.company"].browse(
                res.get("company_id") or self.env.company.id
            )
            kind = res.get("kind") or self._default_kind()
            frequency = company[KIND_SPECS[kind]["frequency_field"]] or "annual"
            today = fields.Date.context_today(self)
            current_start, __ = self._l10n_ca_period_bounds(company, frequency, today)
            res["date_from"], res["date_to"] = self._l10n_ca_period_bounds(
                company, frequency, current_start - timedelta(days=1)
            )
        return res

    @api.model
    def _l10n_ca_period_bounds(self, company, frequency, day):
        """Return the (start, end) of the reporting period containing ``day``.

        Periods are aligned on the fiscal year of the company: months or
        quarters counted from the first day of the fiscal year, or the whole
        fiscal year for an annual filer.
        """
        fiscal_year = company.compute_fiscalyear_dates(day)
        if frequency == "annual":
            return fiscal_year["date_from"], fiscal_year["date_to"]
        step = 1 if frequency == "monthly" else 3
        start = fiscal_year["date_from"]
        while True:
            end = min(
                start + relativedelta(months=step, days=-1), fiscal_year["date_to"]
            )
            if day <= end:
                return start, end
            start = end + timedelta(days=1)

    @api.depends("kind", "date_from", "date_to")
    def _compute_name(self):
        labels = dict(self._fields["kind"]._description_selection(self.env))
        for rec in self:
            period = f"{rec.date_from or ''} - {rec.date_to or ''}"
            rec.name = f"{labels.get(rec.kind, '')} {period}"

    def _l10n_ca_is_annual(self):
        """Whether the period of the return is an annual reporting period.

        A period longer than a quarter is a fiscal year. A shorter one is a
        fiscal year only for an annual filer whose period ends on the last
        day of its fiscal year (a short first or last year). Read from the
        period rather than from the current filing frequency, so a return
        keeps its deadline when the company changes frequency later.
        """
        self.ensure_one()
        if self.date_to > self.date_from + relativedelta(months=3, days=-1):
            return True
        company = self.company_id
        if company[KIND_SPECS[self.kind]["frequency_field"]] != "annual":
            return False
        return company.compute_fiscalyear_dates(self.date_to)["date_to"] == (
            self.date_to
        )

    @api.depends("kind", "date_from", "date_to", "company_id")
    def _compute_date_due(self):
        """Due date: the parameter's number of months after the period end.

        A period ending on the last day of a month is due on the last day of
        the target month (June 30 + 1 month = July 31), as the CRA and
        Revenu Quebec publish their deadlines. A deadline falling on a
        weekend or holiday is not moved to the next business day.
        """
        for rec in self:
            if not rec.date_to or not rec.date_from:
                rec.date_due = False
                continue
            code = (
                "l10n_ca.sales_tax.due_months.annual"
                if rec._l10n_ca_is_annual()
                else "l10n_ca.sales_tax.due_months.periodic"
            )
            months = rec.company_id._l10n_ca_param(code, rec.date_to, default=None)
            if months is None:
                rec.date_due = False
                continue
            due = rec.date_to + relativedelta(months=int(months))
            if (rec.date_to + timedelta(days=1)).day == 1:
                due += relativedelta(day=31)
            rec.date_due = due

    @api.depends("net_tax", "regular_net_tax", "method")
    def _compute_quick_method_gain(self):
        for rec in self:
            rec.quick_method_gain = (
                rec.regular_net_tax - rec.net_tax if rec.method == "quick" else 0.0
            )

    @api.onchange("date_range_id")
    def _onchange_date_range_id(self):
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    @api.constrains("date_from", "date_to", "kind", "company_id")
    def _check_period(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError(_("The period ends before it starts."))
            overlap = self.search(
                [
                    ("id", "!=", rec.id),
                    ("company_id", "=", rec.company_id.id),
                    ("kind", "=", rec.kind),
                    ("date_from", "<=", rec.date_to),
                    ("date_to", ">=", rec.date_from),
                ],
                limit=1,
            )
            if overlap:
                raise ValidationError(
                    _(
                        "The period of %(name)s overlaps the return %(other)s.",
                        name=rec.name,
                        other=overlap.name,
                    )
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft(self):
        if any(rec.state in ("closed", "filed") for rec in self):
            raise UserError(_("Reset a closed or filed return to draft first."))

    # ------------------------------------------------------------------
    # Report evaluation
    # ------------------------------------------------------------------

    def _l10n_ca_report(self):
        self.ensure_one()
        return self.env.ref(KIND_SPECS[self.kind]["report"])

    def _l10n_ca_aml_domain(self, date_from=None, date_to=None):
        """Domain of the journal items a return of this company reads.

        Posted items of the period whose tax is exigible, like the tax
        reports: a cash basis tax counts when its cash basis entry posts.
        """
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", date_from or self.date_from),
            ("date", "<=", date_to or self.date_to),
            *self.env["account.move.line"]._get_tax_exigible_domain(),
        ]

    @api.model
    def _l10n_ca_tag_sign(self, line, tag):
        """Sign that turns ``line.balance`` into its value on ``tag``.

        Same convention as the tax_tags engine of the tax reports: a "-"
        tag (tax_negate) and an inverted line (tax_tag_invert, set on sales
        documents) each flip the sign of the balance.
        """
        sign = -1.0 if tag.tax_negate else 1.0
        return -sign if line.tax_tag_invert else sign

    def _l10n_ca_tags_by_formula(self, expressions):
        tags = expressions._get_matching_tags()
        by_formula = defaultdict(lambda: self.env["account.account.tag"])
        for tag in tags:
            by_formula[tag.with_context(lang="en_US").name[1:]] |= tag
        return by_formula

    def _l10n_ca_tag_balances(self, tags, date_from=None, date_to=None):
        """Return {tag: value} for the journal items of the period."""
        values = defaultdict(float)
        if not tags:
            return values
        domain = self._l10n_ca_aml_domain(date_from, date_to) + [
            ("tax_tag_ids", "in", tags.ids)
        ]
        groups = self.env["account.move.line"]._read_group(
            domain, ["tax_tag_ids", "tax_tag_invert"], ["balance:sum"]
        )
        for tag, invert, balance in groups:
            if tag not in tags:
                continue
            sign = -1.0 if tag.tax_negate else 1.0
            values[tag] += balance * (-sign if invert else sign)
        return values

    def _l10n_ca_evaluate(self, overrides=None):
        """Evaluate every expression of the report of the return.

        ``overrides`` maps (line code, expression label) to a value that
        replaces the computed one, aggregations included, before the
        aggregations that depend on it are evaluated. Engines other than
        tax_tags and aggregation evaluate to 0: the l10n_ca returns do not
        use them. Returns {(line code, label): value}.
        """
        self.ensure_one()
        overrides = overrides or {}
        report = self._l10n_ca_report()
        expressions = report.line_ids.expression_ids
        by_key = {(e.report_line_id.code, e.label): e for e in expressions}
        tags_by_formula = self._l10n_ca_tags_by_formula(expressions)
        all_tags = self.env["account.account.tag"].union(*tags_by_formula.values())
        tag_values = self._l10n_ca_tag_balances(all_tags)
        values = {}

        def value(code, label, stack=()):
            key = (code, label)
            if key in overrides:
                return overrides[key]
            if key in values:
                return values[key]
            if key in stack:
                raise UserError(_("Circular formula on line %s.", code))
            expression = by_key.get(key)
            result = 0.0
            if expression and expression.engine == "tax_tags":
                result = sum(
                    tag_values[tag] for tag in tags_by_formula[expression.formula]
                )
            elif expression and expression.engine == "aggregation":
                result = self._l10n_ca_aggregate(
                    expression,
                    lambda c, lbl: value(c, lbl, stack + (key,)),
                )
            values[key] = result
            return result

        return {key: value(*key) for key in by_key}

    @api.model
    def _l10n_ca_aggregate(self, expression, value):
        """Evaluate an aggregation formula and its bound subformula."""
        formula = expression.formula
        if formula == "sum_children":
            result = sum(
                value(child.code, expression.label)
                for child in expression.report_line_id.children_ids
            )
        else:
            text = _TERM_RE.sub(
                lambda m: repr(float(value(m.group(1), m.group(2)))), formula
            )
            result = float(safe_eval(text))
        subformula = (expression.subformula or "").strip()
        bounds = [float(b) for b in _BOUND_RE.findall(subformula)]
        if subformula.startswith("if_above") and bounds:
            result = result if result > bounds[0] else 0.0
        elif subformula.startswith("if_below") and bounds:
            result = result if result < bounds[0] else 0.0
        elif subformula.startswith("if_between") and len(bounds) == 2:
            result = result if bounds[0] < result < bounds[1] else 0.0
        elif subformula.startswith("round("):
            result = round(result, int(subformula[6:-1]))
        return result

    # ------------------------------------------------------------------
    # Quick method
    # ------------------------------------------------------------------

    def _l10n_ca_tagged_lines(self, tag_formula, date_from=None, date_to=None):
        """Return [(journal item, value on the tag)] for one tag formula."""
        country = self.env.ref("base.ca")
        tags = self.env["account.account.tag"]._get_tax_tags(tag_formula, country.id)
        lines = self.env["account.move.line"].search(
            self._l10n_ca_aml_domain(date_from, date_to)
            + [("tax_tag_ids", "in", tags.ids)]
        )
        result = []
        for line in lines:
            tag = line.tax_tag_ids & tags
            result.append((line, line.balance * self._l10n_ca_tag_sign(line, tag[0])))
        return result

    @api.model
    def _l10n_ca_capital_share(self, line):
        """Return the share, from 0 to 1, of a tax line on capital property.

        A tax line is shared among the base lines of its entry that bear
        its tax, prorated on their amounts; the share is the part of the
        base lines on a capital property account. A tax line without any
        base line in its entry has a share of 0.
        """
        bases = line.move_id.line_ids.filtered(
            lambda b, t=line.tax_line_id: (
                not b.tax_line_id and t in b.tax_ids.flatten_taxes_hierarchy()
            )
        )
        amount = sum(abs(b.balance) for b in bases)
        if not amount:
            return 0.0
        capital = sum(
            abs(b.balance)
            for b in bases
            if b.account_id.account_type in CAPITAL_ACCOUNT_TYPES
        )
        return capital / amount

    def _l10n_ca_quick_eligible(self, tag_formula, date_from, date_to):
        """Return the eligible supplies of a period and the tax left out.

        Eligible supplies are the sales on which the tax of the family was
        charged at a positive rate: zero-rated and exempt supplies carry no
        tax line and are left out. Each tax line gives its base plus its
        tax, signed by the tax so that a credit note reduces the total. The
        share of a tax line on sales of capital property, real property
        included (``_l10n_ca_capital_share``), is not an eligible supply:
        its tax is summed apart, to be remitted in full.

        Returns ({tax rate: tax-included eligible supplies}, tax on the
        sales of capital property).
        """
        eligible = defaultdict(float)
        capital_tax = 0.0
        for line, tax in self._l10n_ca_tagged_lines(tag_formula, date_from, date_to):
            rate = line.tax_line_id.amount
            if line.tax_line_id.type_tax_use != "sale" or rate <= 0:
                continue
            share = self._l10n_ca_capital_share(line)
            base = abs(line.tax_base_amount) * (1.0 if tax >= 0 else -1.0)
            eligible[f"{rate:g}"] += (base + tax) * (1.0 - share)
            capital_tax += tax * share
        return eligible, capital_tax

    def _l10n_ca_zero_rated_supplies(self, date_from, date_to):
        """Return the zero-rated supplies of a period, signed like sales.

        Zero-rated supplies are the journal items whose only taxes are 0%
        sale taxes other than ``exempt_sale_tax_0`` of the ca_2023 chart,
        exports included. Items on a capital property account are left
        out. They carry no tax line, so ``_l10n_ca_quick_eligible`` does
        not see them.
        """
        company = self.company_id
        exempt = (
            self.env["account.chart.template"]
            .with_company(company)
            .ref("exempt_sale_tax_0", raise_if_not_found=False)
        )
        taxes = (
            self.env["account.tax"].search(
                [
                    *self.env["account.tax"]._check_company_domain(company),
                    ("type_tax_use", "=", "sale"),
                    ("amount_type", "=", "percent"),
                    ("amount", "=", 0.0),
                ]
            )
            - exempt
        )
        lines = self.env["account.move.line"].search(
            self._l10n_ca_aml_domain(date_from, date_to)
            + [
                ("tax_ids", "in", taxes.ids),
                ("account_id.account_type", "not in", CAPITAL_ACCOUNT_TYPES),
            ]
        )
        return -sum(line.balance for line in lines if not (line.tax_ids - taxes))

    def _l10n_ca_capital_itc(self, tag_formula):
        """Return the input tax credits of the period on capital property.

        The share of each tax line on capital property
        (``_l10n_ca_capital_share``) is claimable under the quick method.
        """
        return sum(
            tax * self._l10n_ca_capital_share(line)
            for line, tax in self._l10n_ca_tagged_lines(tag_formula)
        )

    def _l10n_ca_quick_rate(self, family, rate_key):
        company = self.company_id
        activity = company.l10n_ca_quick_method_activity or "service"
        if family["tax"] == "qst":
            return company._l10n_ca_param(
                f"l10n_ca.qst_quick.rate.{activity}", self.date_to
            )
        rates = company._l10n_ca_param(
            f"l10n_ca.gst_quick.rates.{activity}", self.date_to
        )
        if rate_key not in rates:
            raise UserError(
                _(
                    "No quick method remittance rate for supplies taxed at "
                    "%(rate)s%% in parameter l10n_ca.gst_quick.rates.%(activity)s.",
                    rate=rate_key,
                    activity=activity,
                )
            )
        return rates[rate_key]

    def _l10n_ca_quick_overrides(self, regular_values):
        """Return the line overrides of the quick method and an explanation.

        Per tax family: collected tax = sum over tax rates of tax-included
        eligible supplies x remittance rate, plus the tax charged on the
        sales of capital property, which are not eligible supplies; ITCs =
        ITCs on capital property; deductions = regular deductions + credit,
        the credit being credit rate x the part of the eligible supplies of
        the period below the yearly ceiling, when the election covers the
        start of the fiscal year. Line 101 follows ``supplies_line`` and
        ``supplies_tax`` of KIND_SPECS. The note warns when the eligible and
        zero-rated supplies of the previous fiscal year exceed the
        eligibility threshold; sales of associates are not in the books and
        are not counted.
        """
        self.ensure_one()
        spec = KIND_SPECS[self.kind]
        company = self.company_id
        currency = self.currency_id
        fiscal_year = company.compute_fiscalyear_dates(self.date_from)
        fy_start = fiscal_year["date_from"]
        election = company.l10n_ca_quick_method_date
        credit_allowed = not election or election <= fy_start
        overrides = {}
        notes = []
        tax_names = {"gst": _("GST/HST"), "qst": _("QST")}

        def money(amount):
            return formatLang(self.env, amount, currency_obj=currency)

        for family in spec["families"]:
            label = family["label"]
            prefix = "qst" if family["tax"] == "qst" else "gst"
            eligible_by_rate, capital_tax = self._l10n_ca_quick_eligible(
                family["collected_tag"], self.date_from, self.date_to
            )
            capital_tax = currency.round(capital_tax)
            remitted = sum(
                currency.round(amount * self._l10n_ca_quick_rate(family, key))
                for key, amount in eligible_by_rate.items()
            )
            eligible = sum(eligible_by_rate.values())
            credit = 0.0
            if credit_allowed:
                before = 0.0
                if self.date_from > fy_start:
                    before = sum(
                        self._l10n_ca_quick_eligible(
                            family["collected_tag"],
                            fy_start,
                            self.date_from - timedelta(days=1),
                        )[0].values()
                    )
                ceiling = company._l10n_ca_param(
                    f"l10n_ca.{prefix}_quick.credit_ceiling", self.date_to
                )
                rate = company._l10n_ca_param(
                    f"l10n_ca.{prefix}_quick.credit_rate", self.date_to
                )
                credit = currency.round(
                    rate * max(0.0, min(eligible, ceiling - before))
                )
            capital_itc = currency.round(self._l10n_ca_capital_itc(family["itc_tag"]))
            deducted_key = (family["deducted_line"], label)
            overrides[(family["collected_line"], label)] = remitted + capital_tax
            overrides[(family["itc_line"], label)] = capital_itc
            overrides[deducted_key] = regular_values.get(deducted_key, 0.0) + credit
            if spec["supplies_line"] and not spec["supplies_tax"]:
                overrides[spec["supplies_line"]] = eligible
            notes.append(
                _(
                    "%(tax)s: eligible supplies %(eligible)s, remitted "
                    "%(remitted)s, tax on sales of capital property "
                    "%(capital_tax)s, credit %(credit)s, capital ITCs %(itc)s.",
                    tax=tax_names[family["tax"]],
                    eligible=money(eligible),
                    remitted=money(remitted),
                    capital_tax=money(capital_tax),
                    credit=money(credit),
                    itc=money(capital_itc),
                )
            )
            threshold = company._l10n_ca_param(
                f"l10n_ca.{prefix}_quick.eligibility_threshold",
                self.date_to,
                default=None,
            )
            if threshold:
                previous = company.compute_fiscalyear_dates(
                    fy_start - timedelta(days=1)
                )
                last_year = sum(
                    self._l10n_ca_quick_eligible(
                        family["collected_tag"],
                        previous["date_from"],
                        previous["date_to"],
                    )[0].values()
                ) + self._l10n_ca_zero_rated_supplies(
                    previous["date_from"], previous["date_to"]
                )
                if last_year > threshold:
                    notes.append(
                        _(
                            "%(tax)s: taxable supplies of the previous fiscal "
                            "year (%(amount)s) exceed the quick method "
                            "threshold of %(threshold)s.",
                            tax=tax_names[family["tax"]],
                            amount=money(last_year),
                            threshold=money(threshold),
                        )
                    )
        if spec["supplies_tax"]:
            overrides[spec["supplies_line"]] = regular_values.get(
                spec["supplies_line"], 0.0
            ) + regular_values.get(spec["supplies_tax"], 0.0)
        if not credit_allowed:
            notes.append(
                _(
                    "No credit: the election does not cover the first day "
                    "of the fiscal year."
                )
            )
        return overrides, "\n".join(notes)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @api.model
    def _l10n_ca_form_numbers(self, report_line):
        """Split "103 - 203 - Label" into (["103", "203"], "Label")."""
        name = report_line.with_context(lang="en_US").name or ""
        match = _FORM_NUMBER_RE.match(name)
        if not match:
            return [], name
        numbers = [n.strip() for n in match.group(1).split("-") if n.strip()]
        return numbers, match.group(2).strip()

    def _l10n_ca_sum(self, values, keys):
        return sum(values.get(key, 0.0) for key in keys)

    def action_compute(self):
        for rec in self:
            if rec.state not in ("draft", "computed"):
                raise UserError(_("Only a draft return can be computed."))
            spec = KIND_SPECS[rec.kind]
            regular = rec._l10n_ca_evaluate()
            values, note = regular, False
            if rec.method == "quick":
                overrides, note = rec._l10n_ca_quick_overrides(regular)
                values = rec._l10n_ca_evaluate(overrides)
            else:
                overrides = {}
            report = rec._l10n_ca_report()
            labels = report.column_ids.sorted("sequence").mapped("expression_label")
            commands = [Command.clear()]
            sequence = 0
            for report_line in report.line_ids.sorted(lambda r: (r.sequence, r.id)):
                if report_line.code in spec["quick_hidden"] and rec.method == "quick":
                    continue
                numbers, __ = rec._l10n_ca_form_numbers(report_line)
                for index, label in enumerate(labels):
                    key = (report_line.code, label)
                    if key not in values:
                        continue
                    sequence += 1
                    commands.append(
                        Command.create(
                            {
                                "sequence": sequence,
                                "code": (
                                    numbers[index]
                                    if index < len(numbers)
                                    else (numbers[0] if numbers else report_line.code)
                                ),
                                "amount": rec.currency_id.round(values[key]),
                                "report_line_id": report_line.id,
                                "expression_label": label,
                                "hierarchy_level": report_line.hierarchy_level,
                                "is_quick_method": key in overrides,
                            }
                        )
                    )
            rec.write(
                {
                    "line_ids": commands,
                    "net_tax": rec.currency_id.round(
                        rec._l10n_ca_sum(values, spec["net_tax"])
                    ),
                    "regular_net_tax": rec.currency_id.round(
                        rec._l10n_ca_sum(regular, spec["net_tax"])
                    ),
                    "amount_due": rec.currency_id.round(
                        rec._l10n_ca_sum(values, spec["amount_due"])
                    ),
                    "quick_method_note": note,
                    "state": "computed",
                }
            )
        return True

    def _l10n_ca_closing_tags(self):
        """Tags whose journal items make the net tax of the return."""
        spec = KIND_SPECS[self.kind]
        report = self._l10n_ca_report()
        expressions = report.line_ids.expression_ids.filtered(
            lambda e: (e.report_line_id.code, e.label) in spec["net_tax"]
        )
        return expressions._expand_aggregations()._get_matching_tags()

    def _l10n_ca_closing_lines(self):
        self.ensure_one()
        return self.env["account.move.line"].search(
            self._l10n_ca_aml_domain()
            + [("tax_tag_ids", "in", self._l10n_ca_closing_tags().ids)]
        )

    def action_close(self):
        """Post the entry that moves the period tax balances to the authority.

        Each account of the journal items that make the net tax is reversed
        for its balance of the period. The authority account receives the
        net tax of the return; under the quick method the gain account
        receives the difference with the tax recorded in the books.
        """
        for rec in self:
            if rec.state != "computed":
                raise UserError(_("Compute the return before closing it."))
            company = rec.company_id
            currency = rec.currency_id
            spec = KIND_SPECS[rec.kind]
            authority = company[spec["authority_field"]]
            if not authority:
                raise UserError(
                    _(
                        "Set the account of the tax authority in the "
                        "accounting settings (Canadian Sales Tax Returns)."
                    )
                )
            journal = company._l10n_ca_tax_closing_journal()
            if not journal:
                raise UserError(_("No miscellaneous journal for the closing entry."))
            other = self.search(
                [
                    ("id", "!=", rec.id),
                    ("company_id", "=", company.id),
                    ("state", "in", ("closed", "filed")),
                    ("date_from", "<=", rec.date_to),
                    ("date_to", ">=", rec.date_from),
                ],
                limit=1,
            )
            if other:
                raise UserError(
                    _(
                        "The return %(other)s already closed tax accounts of "
                        "this period.",
                        other=other.name,
                    )
                )
            balances = defaultdict(float)
            for line in rec._l10n_ca_closing_lines():
                balances[line.account_id] += line.balance
            commands = []
            books = 0.0
            for account, balance in balances.items():
                if currency.is_zero(balance):
                    continue
                books -= balance
                commands.append(
                    Command.create(
                        {
                            "name": rec.name,
                            "account_id": account.id,
                            "balance": -balance,
                        }
                    )
                )
            if currency.compare_amounts(books, rec.regular_net_tax):
                raise UserError(
                    _(
                        "The tax accounts hold %(books).2f for the period but "
                        "the return computes a net tax of %(net).2f in the "
                        "books. Recompute the return.",
                        books=books,
                        net=rec.regular_net_tax,
                    )
                )
            gain = currency.round(books - rec.net_tax)
            if not currency.is_zero(rec.net_tax):
                commands.append(
                    Command.create(
                        {
                            "name": rec.name,
                            "account_id": authority.id,
                            "balance": -rec.net_tax,
                        }
                    )
                )
            gain_account = company.l10n_ca_quick_method_gain_account_id
            if not currency.is_zero(gain):
                if not gain_account:
                    raise UserError(
                        _("Set the quick method gain account in the settings.")
                    )
                commands.append(
                    Command.create(
                        {
                            "name": _("Quick method: %s", rec.name),
                            "account_id": gain_account.id,
                            "balance": -gain,
                        }
                    )
                )
            if not commands:
                rec.state = "closed"
                continue
            move = (
                self.env["account.move"]
                .with_company(company)
                .create(
                    {
                        "move_type": "entry",
                        "journal_id": journal.id,
                        "date": rec.date_to,
                        "ref": rec.name,
                        "line_ids": commands,
                    }
                )
            )
            move.action_post()
            rec.write({"closing_move_id": move.id, "state": "closed"})
        return True

    def action_mark_filed(self):
        for rec in self:
            if rec.state != "closed":
                raise UserError(_("Close the return before marking it filed."))
            rec.write(
                {
                    "state": "filed",
                    "filing_date": rec.filing_date or fields.Date.context_today(rec),
                }
            )
        return True

    def action_reset_to_draft(self):
        for rec in self:
            move = rec.closing_move_id
            if move:
                if move.state == "posted":
                    move.button_draft()
                # A move that consumed a sequence number in the middle of
                # its journal, or that the audit trail keeps, cannot be
                # deleted: it is cancelled instead, which takes it out of
                # the posted balances all the same.
                try:
                    with self.env.cr.savepoint():
                        move.unlink()
                except UserError:
                    move.button_cancel()
            rec.write(
                {
                    "state": "draft",
                    "closing_move_id": False,
                    "line_ids": [Command.clear()],
                }
            )
        return True

    def action_open_closing_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.closing_move_id.id,
            "view_mode": "form",
        }

    def action_print_xlsx(self):
        return self.env.ref(
            "l10n_ca_tax_return.action_report_tax_return_xlsx"
        ).report_action(self)


class L10nCaTaxReturnLine(models.Model):
    _name = "l10n.ca.tax.return.line"
    _description = "Canadian Sales Tax Return Line"
    _order = "return_id, sequence, id"

    return_id = fields.Many2one(
        "l10n.ca.tax.return", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="return_id.company_id", store=True)
    currency_id = fields.Many2one(related="return_id.currency_id")
    sequence = fields.Integer()
    code = fields.Char(string="Line", required=True)
    name = fields.Char(string="Description", compute="_compute_name")
    amount = fields.Monetary()
    report_line_id = fields.Many2one("account.report.line", readonly=True)
    expression_label = fields.Char(readonly=True)
    hierarchy_level = fields.Integer()
    is_quick_method = fields.Boolean(
        string="Quick Method",
        help="Amount computed by the quick method instead of the tax tags.",
    )

    @api.depends("report_line_id", "expression_label")
    @api.depends_context("lang")
    def _compute_name(self):
        """Label of the form line in the language of the reader.

        Read from the report line rather than stored, so a return computed
        by one user reads in the language of each user, and the PDF in the
        language of the company. The form numbers that open the report line
        name ("103 - 203 - ") are left out: the line code shows them. When
        the report line has a value in several columns of its report (the
        GST/HST and QST columns of the FPZ-500), the name of the column of
        this line follows, so that lines 103 and 203 do not read the same.
        """
        for line in self:
            report_line = line.report_line_id
            name = report_line.name or ""
            match = _FORM_NUMBER_RE.match(name)
            name = match.group(2).strip() if match else name
            columns = report_line.report_id.column_ids
            labels = set(report_line.expression_ids.mapped("label")) & set(
                columns.mapped("expression_label")
            )
            if len(labels) > 1:
                column = columns.filtered(
                    lambda c, lbl=line.expression_label: c.expression_label == lbl
                )[:1]
                if column.name:
                    name = f"{name} ({column.name})"
            line.name = name

    def action_open_move_lines(self):
        """Open the journal items behind the line.

        Follows the aggregation formulas of the line down to its tax tags,
        so a total opens every item it sums.
        """
        self.ensure_one()
        tax_return = self.return_id
        expression = self.report_line_id.expression_ids.filtered(
            lambda e: e.label == self.expression_label
        )
        tags = expression._expand_aggregations()._get_matching_tags()
        domain = tax_return._l10n_ca_aml_domain() + [("tax_tag_ids", "in", tags.ids)]
        return {
            "type": "ir.actions.act_window",
            "name": _("Line %(code)s - %(name)s", code=self.code, name=self.name),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("account.view_move_line_tree").id, "list"),
                (False, "form"),
            ],
            "domain": domain,
            "context": {"search_default_group_by_move": 0, "create": False},
        }
