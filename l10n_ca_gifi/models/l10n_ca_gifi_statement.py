# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import csv
import io
from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, format_amount, formatLang

SCHEDULES = [
    ("100", "Schedule 100 - Balance Sheet"),
    ("101", "Schedule 101 - Opening Balance Sheet"),
    ("125", "Schedule 125 - Income Statement"),
]
CHECK_LEVELS = [("error", "Error"), ("warning", "Warning"), ("info", "Information")]

# Closing types of the OCA module account_fiscal_year_closing whose entries
# are ignored like those of the closing journals.
_OCA_CLOSING_TYPES = ("closing", "opening", "loss_profit")


def round_dollars(amount):
    """Round to whole dollars, half away from zero (10,500.75 -> 10,501)."""
    return float_round(amount, precision_digits=0, rounding_method="HALF-UP")


class L10nCaGifiStatement(models.Model):
    """GIFI trial balance of one fiscal year.

    ``action_compute`` reads the posted entries and stores one line per
    reported GIFI item: Schedule 100 at the end of the year (with the
    retained earnings section 3660-3849), Schedule 125 for the year and,
    for the first year after incorporation, Schedule 101 at the start of
    the year. Amounts are whole dollars; totals are sums of the rounded
    items, so that they match what the tax software recomputes.
    """

    _name = "l10n.ca.gifi.statement"
    _description = "GIFI Statement"
    _order = "date_to desc, id desc"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date_range_id = fields.Many2one(
        "date.range",
        string="Fiscal Year",
        check_company=True,
        help="Fills the dates from a date range.",
    )
    date_from = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: self._default_dates()[0],
    )
    date_to = fields.Date(
        string="End Date", required=True, default=lambda self: self._default_dates()[1]
    )
    first_year = fields.Boolean(
        string="First Year After Incorporation",
        compute="_compute_first_year",
        store=True,
        readonly=False,
        help="Adds Schedule 101, the opening balance sheet. Set when no "
        "entry is posted before the start date.",
    )
    computed_on = fields.Datetime(readonly=True)
    line_ids = fields.One2many("l10n.ca.gifi.statement.line", "statement_id")
    s100_line_ids = fields.One2many(
        "l10n.ca.gifi.statement.line",
        "statement_id",
        domain=[("schedule", "=", "100")],
        string="Schedule 100",
    )
    s101_line_ids = fields.One2many(
        "l10n.ca.gifi.statement.line",
        "statement_id",
        domain=[("schedule", "=", "101")],
        string="Schedule 101",
    )
    s125_line_ids = fields.One2many(
        "l10n.ca.gifi.statement.line",
        "statement_id",
        domain=[("schedule", "=", "125")],
        string="Schedule 125",
    )
    check_ids = fields.One2many(
        "l10n.ca.gifi.statement.check", "statement_id", string="Checks"
    )
    error_count = fields.Integer(compute="_compute_check_counts")
    warning_count = fields.Integer(compute="_compute_check_counts")
    total_assets = fields.Float(digits=(16, 0), readonly=True)
    net_income = fields.Float(digits=(16, 0), readonly=True)

    @api.model
    def _default_dates(self):
        """Return the last fiscal year of the company ended before today."""
        company = self.env.company
        today = fields.Date.context_today(self)
        fiscal_year = company.compute_fiscalyear_dates(today)
        if fiscal_year["date_to"] >= today:
            fiscal_year = company.compute_fiscalyear_dates(
                fiscal_year["date_from"] - timedelta(days=1)
            )
        return fiscal_year["date_from"], fiscal_year["date_to"]

    @api.depends("company_id", "date_to")
    def _compute_name(self):
        for statement in self:
            statement.name = _(
                "GIFI %(date)s - %(company)s",
                date=statement.date_to or "",
                company=statement.company_id.name or "",
            )

    @api.depends("company_id", "date_from")
    def _compute_first_year(self):
        for statement in self:
            statement.first_year = bool(statement.date_from) and not self.env[
                "account.move.line"
            ].search_count(
                [
                    ("company_id", "child_of", statement.company_id.id),
                    ("parent_state", "=", "posted"),
                    ("date", "<", statement.date_from),
                ],
                limit=1,
            )

    @api.depends("check_ids.level")
    def _compute_check_counts(self):
        for statement in self:
            levels = statement.check_ids.mapped("level")
            statement.error_count = levels.count("error")
            statement.warning_count = levels.count("warning")

    @api.onchange("date_range_id")
    def _onchange_date_range_id(self):
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for statement in self:
            if statement.date_from > statement.date_to:
                raise ValidationError(_("The start date must precede the end date."))

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def _move_line_domain(self):
        """Posted lines of the company and its branches, closing entries
        excluded (closing journals, and the closing types of the OCA
        module account_fiscal_year_closing when it is installed)."""
        self.ensure_one()
        domain = [
            ("company_id", "child_of", self.company_id.id),
            ("parent_state", "=", "posted"),
        ]
        journals = self.company_id.l10n_ca_gifi_closing_journal_ids
        if journals:
            domain.append(("journal_id", "not in", journals.ids))
        if "closing_type" in self.env["account.move"]._fields:
            domain.append(("move_id.closing_type", "not in", _OCA_CLOSING_TYPES))
        return domain

    def _balances(self, date_domain):
        """Return ``{account: debit - credit}`` for the lines in range."""
        groups = self.env["account.move.line"]._read_group(
            self._move_line_domain() + date_domain,
            groupby=["account_id"],
            aggregates=["balance:sum"],
        )
        return {account: balance for account, balance in groups}

    def action_compute(self):
        for statement in self:
            statement._compute_gifi()
        return True

    def _check_branches_selected(self):
        """Raise when a branch of the company is not among the companies
        selected in the switcher: the record rules would hide its entries
        and the statement would silently omit them."""
        self.ensure_one()
        branches = (
            self.env["res.company"]
            .sudo()
            .search([("id", "child_of", self.company_id.id)])
        )
        missing = branches - self.env.companies
        if missing:
            raise UserError(
                _(
                    "Select the company and all its branches (%s) in the "
                    "company switcher before computing the GIFI statement.",
                    ", ".join(missing.mapped("name")),
                )
            )

    def _compute_gifi(self):
        self.ensure_one()
        self._check_branches_selected()
        engine = _GifiEngine(self)
        engine.run()
        self.line_ids.unlink()
        self.check_ids.unlink()
        self.write(
            {
                "line_ids": [fields.Command.create(vals) for vals in engine.lines],
                "check_ids": [fields.Command.create(vals) for vals in engine.checks],
                "computed_on": fields.Datetime.now(),
                "total_assets": engine.value("100", "2599"),
                "net_income": engine.value("125", "9999"),
            }
        )

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def _csv_content(self, schedule):
        """Return the ``code,amount`` lines of ``schedule``, amounts in
        whole dollars, ordered by code, without header: the generic GIFI
        import of the T2 software."""
        self.ensure_one()
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        lines = self.line_ids.filtered(lambda line: line.schedule == schedule)
        for line in lines.sorted("code"):
            writer.writerow([line.code, int(line.amount)])
        return buffer.getvalue()

    def action_export_csv(self):
        self.ensure_one()
        schedule = self.env.context.get("gifi_schedule", "100")
        if not self.line_ids:
            raise UserError(_("Compute the statement before exporting it."))
        content = self._csv_content(schedule)
        filename = f"GIFI_S{schedule}_{self.date_to.isoformat()}.csv"
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(content.encode("utf-8")),
                "mimetype": "text/csv",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_print_pdf(self):
        return self.env.ref("l10n_ca_gifi.action_report_gifi_statement").report_action(
            self
        )

    def action_print_xlsx(self):
        return self.env.ref(
            "l10n_ca_gifi.action_report_gifi_statement_xlsx"
        ).report_action(self)

    def _lines_of(self, schedule):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.schedule == schedule).sorted(
            "code"
        )


class L10nCaGifiStatementLine(models.Model):
    _name = "l10n.ca.gifi.statement.line"
    _description = "GIFI Statement Line"
    _order = "statement_id, schedule, code"

    statement_id = fields.Many2one(
        "l10n.ca.gifi.statement", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="statement_id.company_id", store=True)
    schedule = fields.Selection(SCHEDULES, required=True)
    gifi_code_id = fields.Many2one(
        "l10n.ca.gifi.code", string="GIFI Code", required=True, ondelete="restrict"
    )
    code = fields.Char(related="gifi_code_id.code", store=True)
    name = fields.Char(related="gifi_code_id.name")
    category = fields.Selection(related="gifi_code_id.category", store=True)
    is_total = fields.Boolean(related="gifi_code_id.is_total", store=True)
    amount = fields.Float(digits=(16, 0), help="Whole dollars, as reported.")
    amount_exact = fields.Float(
        digits=(16, 2), help="Amount before rounding to whole dollars."
    )
    account_ids = fields.Many2many(
        "account.account",
        "l10n_ca_gifi_statement_line_account_rel",
        "line_id",
        "account_id",
        string="Accounts",
    )


class L10nCaGifiStatementCheck(models.Model):
    _name = "l10n.ca.gifi.statement.check"
    _description = "GIFI Statement Check"
    _order = "statement_id, sequence, id"

    statement_id = fields.Many2one(
        "l10n.ca.gifi.statement", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="statement_id.company_id", store=True)
    sequence = fields.Integer()
    level = fields.Selection(CHECK_LEVELS, required=True)
    message = fields.Text(required=True)
    gifi_code_id = fields.Many2one("l10n.ca.gifi.code", string="GIFI Code")
    account_id = fields.Many2one("account.account")


class _GifiEngine:
    """Computation of the GIFI schedules of one statement.

    Every reported amount is held per ``(schedule, code)`` in ``exact``
    (currency amounts) and ``amounts`` (whole dollars). Retained earnings:
    closing entries are excluded, so the income statement accounts carry
    the results of every past year; item 3600 is the balance of the
    accounts mapped to the retained earnings items plus the cumulative
    balance of every income statement account at that date, except the
    other comprehensive income items, which accumulate in 3580. The
    roll-forward 3660 -> 3849 uses the same pools at the start and the end
    of the year, so that 3849 equals 3600 before rounding.
    """

    RETAINED_EARNINGS = "3600"
    UNCLASSIFIED_RE = "3740"
    ACCUMULATED_OCI = "3580"
    PURCHASES = "8320"
    INVENTORY_CODES = (
        ("100", ("1120", "1121", "1122", "1123", "1124", "1125", "1126", "1127")),
        ("125", ("8300", "8301", "8302", "8303", "8500", "8501", "8502", "8503")),
    )

    def __init__(self, statement):
        self.statement = statement
        self.env = statement.env
        self.company = statement.company_id
        self.currency = self.company.currency_id
        Code = self.env["l10n.ca.gifi.code"].with_context(active_test=False)
        self.codes = {code.code: code for code in Code.search([])}
        self.exact = defaultdict(float)
        self.amounts = {}
        self.accounts = defaultdict(set)
        self.computed = {}
        self.lines = []
        self.checks = []

    # -- helpers -------------------------------------------------------

    def code(self, code):
        return self.codes[code]

    def check(self, level, message, code=None, account=None):
        self.checks.append(
            {
                "sequence": {"error": 1, "warning": 2, "info": 3}[level],
                "level": level,
                "message": message,
                "gifi_code_id": code.id if code else False,
                "account_id": account.id if account else False,
            }
        )

    def add(self, schedule, code, amount, account=None):
        self.exact[(schedule, code.code)] += amount
        if account is not None:
            self.accounts[(schedule, code.code)].add(account.id)

    def value(self, schedule, code):
        """Rounded amount of ``code`` in ``schedule``, totals included."""
        key = (schedule, code)
        if key in self.computed:
            return self.computed[key]
        record = self.code(code)
        if record.formula:
            result = sum(
                sign * self.value(schedule, term)
                for sign, term in record._formula_terms()
            )
        elif record.is_total and key not in self.amounts:
            result = sum(
                component.total_sign * self.value(schedule, component.code)
                for component in record.component_ids
            )
        else:
            result = self.amounts.get(key, 0.0)
        self.computed[key] = result
        return result

    def reset_totals(self):
        self.computed = {}

    # -- steps ---------------------------------------------------------

    def run(self):
        statement = self.statement
        date_from, date_to = statement.date_from, statement.date_to
        end = statement._balances([("date", "<=", date_to)])
        opening = statement._balances([("date", "<", date_from)])
        period = statement._balances(
            [("date", ">=", date_from), ("date", "<=", date_to)]
        )
        accounts = self.env["account.account"].browse(
            list({a.id for a in (*end, *opening, *period)})
        )
        mapping = accounts._l10n_ca_gifi_code_map(self.company)
        re_pool = {"100": 0.0, "101": 0.0}
        for account in accounts.sorted("code"):
            balances = (
                end.get(account, 0.0),
                opening.get(account, 0.0),
                period.get(account, 0.0),
            )
            if all(self.currency.is_zero(b) for b in balances):
                continue
            code, source = mapping[account]
            if account.account_type == "off_balance":
                continue
            if not code:
                self.check(
                    "error",
                    self.env._(
                        "Account %(account)s has no GIFI code: its balance "
                        "%(balance)s is not reported.",
                        account=account.display_name,
                        balance=self._fmt(balances[0]),
                    ),
                    account=account,
                )
                continue
            if source == "type":
                self.check(
                    "info",
                    self.env._(
                        "Account %(account)s is reported under %(code)s by "
                        "the fallback of its account type.",
                        account=account.display_name,
                        code=code.display_name,
                    ),
                    code=code,
                    account=account,
                )
            self._check_account_schedule(account, code)
            if code.partnership_only:
                self.check(
                    "warning",
                    self.env._(
                        "GIFI item %(code)s is reserved to partnerships "
                        "(account %(account)s).",
                        code=code.display_name,
                        account=account.display_name,
                    ),
                    code=code,
                    account=account,
                )
            self._dispatch(account, code, balances, re_pool)
        self._round_details()
        self._balance_sheet("101", re_pool["101"])
        self._balance_sheet("100", re_pool["100"])
        self._retained_earnings()
        self._consistency_checks()
        self._purchases_check()
        self._gifi_short_eligibility()
        self._build_lines()

    def _dispatch(self, account, code, balances, re_pool):
        end_balance, opening_balance, period_balance = balances
        if code.schedule == "125":
            self.add("125", code, code._amount_sign() * period_balance, account)
            if code.category == "other_comprehensive_income":
                # Other comprehensive income accumulates in 3580, not in
                # retained earnings: 3680 excludes it (9999 - 9998).
                aoci = self.code(self.ACCUMULATED_OCI)
                sign = aoci._amount_sign()
                self.add("100", aoci, sign * end_balance, account)
                self.add("101", aoci, sign * opening_balance, account)
                return
            re_pool["100"] -= end_balance
            re_pool["101"] -= opening_balance
        elif (
            code.category == "retained_earnings" or code.code == self.RETAINED_EARNINGS
        ):
            re_pool["100"] -= end_balance
            re_pool["101"] -= opening_balance
            self.accounts[("100", self.RETAINED_EARNINGS)].add(account.id)
            target = code
            if code.code == self.RETAINED_EARNINGS:
                if self.currency.is_zero(period_balance):
                    return
                target = self.code(self.UNCLASSIFIED_RE)
                self.check(
                    "warning",
                    self.env._(
                        "Entries of %(amount)s on retained earnings account "
                        "%(account)s during the year are reported under "
                        "%(code)s. Map a dividends account to 3700 or set "
                        "the closing journal in the settings.",
                        amount=self._fmt(-period_balance),
                        account=account.display_name,
                        code=target.display_name,
                    ),
                    code=target,
                    account=account,
                )
            self.add("100", target, target._amount_sign() * period_balance, account)
        else:
            sign = code._amount_sign()
            self.add("100", code, sign * end_balance, account)
            self.add("101", code, sign * opening_balance, account)

    def _check_account_schedule(self, account, code):
        group = account.internal_group
        if (
            group in ("income", "expense")
            and code.schedule == "100"
            and code.category != "retained_earnings"
        ):
            message = self.env._(
                "Income statement account %(account)s is mapped to balance "
                "sheet item %(code)s.",
                account=account.display_name,
                code=code.display_name,
            )
        elif group in ("asset", "liability", "equity") and code.schedule == "125":
            message = self.env._(
                "Balance sheet account %(account)s is mapped to income "
                "statement item %(code)s.",
                account=account.display_name,
                code=code.display_name,
            )
        else:
            return
        self.check("warning", message, code=code, account=account)

    def _round_details(self):
        for key, amount in self.exact.items():
            self.amounts[key] = round_dollars(amount)

    def _rounding_tolerance(self, *schedules):
        """Largest gap that rounding the items to dollars can open: half a
        dollar per rounded item, plus one."""
        count = sum(1 for (schedule, _code) in self.amounts if schedule in schedules)
        return count * 0.5 + 1

    def _balance_sheet(self, schedule, re_pool):
        """Set 3600 so that total assets equal liabilities plus equity.

        The exact retained earnings make the balance sheet balance before
        rounding; after rounding, a gap within the rounding tolerance is
        absorbed by 3600 and reported. A larger gap is left visible: it
        comes from an unreported account, not from rounding.
        """
        key = (schedule, self.RETAINED_EARNINGS)
        self.exact[key] = re_pool
        self.amounts[key] = round_dollars(re_pool)
        self.reset_totals()
        gap = self.value(schedule, "2599") - (
            self.value(schedule, "3499") + self.value(schedule, "3620")
        )
        if gap and abs(gap) <= self._rounding_tolerance(schedule):
            self.amounts[key] += gap
            self.reset_totals()
            self.check(
                "info",
                self.env._(
                    "Schedule %(schedule)s: rounding difference of %(gap)s "
                    "absorbed by item 3600.",
                    schedule=schedule,
                    gap=self._fmt_dollars(gap),
                ),
                code=self.code(self.RETAINED_EARNINGS),
            )

    def _retained_earnings(self):
        """Fill 3660 and 3680, then reconcile 3849 with 3600."""
        self.reset_totals()
        self.amounts[("100", "3660")] = self.value("101", self.RETAINED_EARNINGS)
        self.exact[("100", "3660")] = self.exact[("101", self.RETAINED_EARNINGS)]
        self.amounts[("100", "3680")] = self.value("125", "9999") - self.value(
            "125", "9998"
        )
        self.exact[("100", "3680")] = self.amounts[("100", "3680")]
        self.reset_totals()
        gap = self.value("100", self.RETAINED_EARNINGS) - self.value("100", "3849")
        if gap and abs(gap) <= self._rounding_tolerance("100", "101", "125"):
            key = ("100", self.UNCLASSIFIED_RE)
            self.amounts[key] = self.amounts.get(key, 0.0) + gap
            self.reset_totals()
            self.check(
                "info",
                self.env._(
                    "Rounding difference of %(gap)s between 3849 and 3600 "
                    "reported under item 3740.",
                    gap=self._fmt_dollars(gap),
                ),
                code=self.code(self.UNCLASSIFIED_RE),
            )

    def _consistency_checks(self):
        self.reset_totals()
        value = self.value
        pairs = [
            (
                "100",
                "2599",
                value("100", "3499") + value("100", "3620"),
                self.env._(
                    "Total assets (2599) differ from total liabilities and "
                    "shareholder equity (3499 + 3620) by %(gap)s."
                ),
            ),
            (
                "100",
                "3849",
                value("100", "3600"),
                self.env._(
                    "Retained earnings at the end (3849) differ from the "
                    "balance sheet retained earnings (3600) by %(gap)s."
                ),
            ),
            (
                "100",
                "3680",
                value("125", "9999") - value("125", "9998"),
                self.env._("Net income (3680) differs from item 9999 by %(gap)s."),
            ),
            (
                "125",
                "9369",
                value("125", "8299") - value("125", "9368"),
                self.env._(
                    "Net non-farming income (9369) differs from total revenue "
                    "less total expenses by %(gap)s."
                ),
            ),
        ]
        if self.statement.first_year:
            pairs.append(
                (
                    "101",
                    "2599",
                    value("101", "3499") + value("101", "3620"),
                    self.env._(
                        "Schedule 101: total assets differ from total "
                        "liabilities and shareholder equity by %(gap)s."
                    ),
                )
            )
        for schedule, code, expected, message in pairs:
            gap = value(schedule, code) - expected
            if gap:
                self.check(
                    "error",
                    message % {"gap": self._fmt_dollars(gap)},
                    code=self.code(code),
                )
        for (schedule, code), amount in sorted(self.amounts.items()):
            record = self.code(code)
            if schedule == "101" and not self.statement.first_year:
                continue
            if record.expected_sign == "positive" and amount < 0:
                text = self.env._(
                    "Item %(code)s is negative (%(amount)s); check the "
                    "mapping of its accounts."
                )
            elif record.expected_sign == "negative" and amount > 0:
                text = self.env._(
                    "Item %(code)s is positive (%(amount)s); a contra "
                    "account is expected to be negative."
                )
            else:
                continue
            self.check(
                "warning",
                text
                % {"code": record.display_name, "amount": self._fmt_dollars(amount)},
                code=record,
            )

    def _purchases_check(self):
        """Warn when 8320 Purchases/cost of materials has an amount while
        no inventory is reported.

        The default expense account of the Canadian chart (511210
        Purchases) is mapped to 8320, so every vendor bill line without a
        more specific account lands in the cost of sales. A business
        without inventory, such as a service business, usually reports
        those costs as operating expenses (rent, software,
        telecommunications, ...).
        """
        purchases = self.value("125", self.PURCHASES)
        if not purchases:
            return
        for schedule, codes in self.INVENTORY_CODES:
            if any(self.value(schedule, code) for code in codes):
                return
        account_ids = sorted(self.accounts.get(("125", self.PURCHASES), ()))
        self.check(
            "warning",
            self.env._(
                "Item %(code)s holds %(amount)s while no inventory is "
                "reported. Check that these costs are purchases of goods or "
                "materials; operating expenses (rent, software, "
                "telecommunications, ...) belong to accounts mapped to the "
                "operating expense items (8520 to 9286).",
                code=self.code(self.PURCHASES).display_name,
                amount=self._fmt_dollars(purchases),
            ),
            code=self.code(self.PURCHASES),
            account=self.env["account.account"].browse(account_ids[:1]),
        )

    def _gifi_short_eligibility(self):
        company, date = self.company, self.statement.date_to
        max_revenue = company._l10n_ca_param(
            "l10n_ca.gifi.short_max_gross_revenue", date, default=None
        )
        max_assets = company._l10n_ca_param(
            "l10n_ca.gifi.short_max_assets", date, default=None
        )
        if max_revenue is None or max_assets is None:
            return
        revenue = self.value("125", "8299") + self.value("125", "9659")
        assets = self.value("100", "2599")
        if revenue < max_revenue and assets < max_assets:
            self.check(
                "info",
                self.env._(
                    "Gross revenue (%(revenue)s) and total assets "
                    "(%(assets)s) are under the GIFI-Short limits: the paper "
                    "form T1178 may be used instead of the GIFI schedules.",
                    revenue=self._fmt_dollars(revenue),
                    assets=self._fmt_dollars(assets),
                ),
            )

    def _build_lines(self):
        """One line per item with an amount, plus the required items."""
        self.reset_totals()
        schedules = ["100", "125"] + (["101"] if self.statement.first_year else [])
        for schedule in schedules:
            base = "125" if schedule == "125" else "100"
            for code, record in sorted(self.codes.items()):
                if record.schedule != base:
                    continue
                if schedule == "101" and record.category == "retained_earnings":
                    continue
                amount = self.value(schedule, code)
                if not amount and not record.required:
                    continue
                key = (schedule, code)
                self.lines.append(
                    {
                        "schedule": schedule,
                        "gifi_code_id": record.id,
                        "amount": amount,
                        "amount_exact": self.exact.get(key, amount),
                        "account_ids": [
                            fields.Command.set(sorted(self.accounts.get(key, ())))
                        ],
                    }
                )

    def _fmt(self, amount):
        """Amount with the separators of the user's language, for the
        check messages."""
        return format_amount(self.env, amount, self.currency)

    def _fmt_dollars(self, amount):
        """Whole-dollar amount of a GIFI item, with the separators and the
        currency symbol of the user's language, for the check messages."""
        return formatLang(
            self.env, amount, currency_obj=self.currency, rounding_unit="units"
        )
