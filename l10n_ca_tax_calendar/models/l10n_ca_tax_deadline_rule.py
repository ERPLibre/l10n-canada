# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from ..tools import (
    BusinessCalendar,
    add_months,
    calendar_periods,
    fiscal_periods,
    fixed_date,
)

AUTHORITIES = [
    ("cra", "Canada Revenue Agency"),
    ("rq", "Revenu Quebec"),
    ("req", "Registraire des entreprises"),
    ("cnesst", "CNESST"),
]

CATEGORIES = [
    ("sales_tax", "Sales Taxes"),
    ("income_tax", "Income Tax"),
    ("payroll", "Payroll"),
    ("registry", "Enterprise Register"),
]

PERIOD_TYPES = [
    ("fiscal_month", "Fiscal month"),
    ("fiscal_quarter", "Fiscal quarter"),
    ("fiscal_year", "Fiscal year"),
    ("month", "Calendar month"),
    ("semi_month", "Half month (1-15, 16-end)"),
    ("quarter_month", "Quarter of month (1-7, 8-14, 15-21, 22-end)"),
    ("quarter", "Calendar quarter"),
    ("year", "Calendar year"),
]

FISCAL_MONTHS = {"fiscal_month": 1, "fiscal_quarter": 3, "fiscal_year": 12}

TIMING_KEYS = {
    "months",
    "days",
    "business_days",
    "fixed_month",
    "fixed_day",
    "fixed_year_offset",
}


class L10nCaTaxDeadlineRule(models.Model):
    _name = "l10n.ca.tax.deadline.rule"
    _description = "Canadian Tax Deadline Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    authority = fields.Selection(AUTHORITIES, required=True)
    category = fields.Selection(CATEGORIES, required=True)
    description = fields.Text(
        translate=True,
        help="Legal rule behind the deadline and its official sources.",
    )
    condition_domain = fields.Char(
        string="Applies When",
        default="[]",
        required=True,
        help="Domain on the company: the rule creates deadlines only for the "
        "companies that match it, e.g. the filing frequency of the tax "
        "profile.",
    )
    period_type = fields.Selection(
        PERIOD_TYPES,
        required=True,
        help="Periods whose end anchors the due date. Fiscal periods follow "
        "the fiscal year end of the company, the others the calendar.",
    )
    timing_param_code = fields.Char(
        string="Timing Parameter",
        help="Code of a dated JSON time parameter holding the timing, read at "
        "the period end. Keys: months, days, business_days (true: days are "
        "business days), fixed_month, fixed_day, fixed_year_offset. When "
        "set, it replaces the timing fields below.",
    )
    offset_months = fields.Integer(
        help="Months added to the period end; a period ending on the last "
        "day of a month gives the last day of the target month.",
    )
    offset_days = fields.Integer(help="Days added after the months.")
    offset_business_days = fields.Boolean(
        help="Count the days as business days of the authority.",
    )
    fixed_month = fields.Integer(
        help="When set (1-12), the due date is a fixed day of this month "
        "instead of an offset from the period end.",
    )
    fixed_day = fields.Integer(
        default=31,
        help="Day of the fixed date; a day past the end of the month means "
        "its last day (31 in February is the last day of February).",
    )
    fixed_year_offset = fields.Integer(
        default=1,
        help="Year of the fixed date relative to the year of the period end.",
    )
    due_date_shift = fields.Selection(
        [
            ("next_business_day", "Next business day"),
            ("none", "No shift"),
        ],
        string="Weekend and Holiday Rule",
        default="next_business_day",
        required=True,
        help="Next business day: a due date on a Saturday, a Sunday or a "
        "public holiday of the authority moves to the next business day.",
    )
    holiday_jurisdiction = fields.Selection(
        [
            ("federal", "Federal"),
            ("quebec", "Quebec"),
            ("quebec_payroll", "Quebec, Revenu Quebec closures included"),
        ],
        compute="_compute_holiday_jurisdiction",
        store=True,
        readonly=False,
        help="Public holidays used for the weekend and holiday rule and for "
        "business days. The source deduction remittances to Revenu Quebec "
        "also skip the days its offices are closed.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        help="Receives the reminders of this rule instead of the responsible "
        "set in the company settings.",
    )
    deadline_ids = fields.One2many("l10n.ca.tax.deadline", "rule_id")
    current_timing = fields.Char(compute="_compute_current_timing")

    _sql_constraints = [
        (
            "code_uniq",
            "UNIQUE(code)",
            "The code of a tax deadline rule must be unique.",
        ),
    ]

    @api.depends("authority")
    def _compute_holiday_jurisdiction(self):
        for rule in self:
            rule.holiday_jurisdiction = (
                "federal" if rule.authority == "cra" else "quebec"
            )

    def _compute_current_timing(self):
        today = fields.Date.context_today(self)
        for rule in self:
            try:
                rule.current_timing = str(rule._l10n_ca_timing(self.env.company, today))
            except UserError as error:
                rule.current_timing = str(error)

    @api.constrains("condition_domain")
    def _check_condition_domain(self):
        for rule in self:
            try:
                domain = safe_eval(rule.condition_domain or "[]")
                self.env.company.filtered_domain(domain)
            except Exception as error:
                raise ValidationError(
                    _(
                        "Invalid condition on rule %(rule)s: %(error)s",
                        rule=rule.code,
                        error=error,
                    )
                ) from error

    @api.constrains("fixed_month")
    def _check_fixed_month(self):
        for rule in self:
            if rule.fixed_month and not 1 <= rule.fixed_month <= 12:
                raise ValidationError(_("The fixed month must be between 1 and 12."))

    def _l10n_ca_applies(self, company):
        """Return whether ``company`` matches the condition of the rule."""
        self.ensure_one()
        domain = safe_eval(self.condition_domain or "[]")
        return bool(company.filtered_domain(domain))

    def _l10n_ca_timing(self, company, on_date):
        """Return the timing dict of the rule for a period ending ``on_date``.

        Read from the dated parameter when the rule names one, so a change
        of law is a new parameter version and past periods keep their
        deadline; else built from the fields of the rule.
        """
        self.ensure_one()
        if self.timing_param_code:
            timing = company._l10n_ca_param(self.timing_param_code, on_date)
            if not isinstance(timing, dict) or set(timing) - TIMING_KEYS:
                raise UserError(
                    _(
                        "Time parameter %(code)s must be a JSON object with the "
                        "keys %(keys)s.",
                        code=self.timing_param_code,
                        keys=", ".join(sorted(TIMING_KEYS)),
                    )
                )
            return timing
        timing = {
            "months": self.offset_months,
            "days": self.offset_days,
            "business_days": self.offset_business_days,
        }
        if self.fixed_month:
            timing.update(
                fixed_month=self.fixed_month,
                fixed_day=self.fixed_day,
                fixed_year_offset=self.fixed_year_offset,
            )
        return timing

    def _l10n_ca_business_calendar(self, company):
        self.ensure_one()
        jurisdiction = self.holiday_jurisdiction or (
            "federal" if self.authority == "cra" else "quebec"
        )

        def holidays_of_year(year):
            return company._l10n_ca_holidays(jurisdiction, year)

        return BusinessCalendar(holidays_of_year)

    def _l10n_ca_periods(self, company, date_from, date_to):
        """Return the periods ``(start, end)`` of the rule ending in the range."""
        self.ensure_one()
        if self.period_type in FISCAL_MONTHS:

            def fiscal_year_dates(day):
                dates = company.compute_fiscalyear_dates(day)
                return (
                    fields.Date.to_date(dates["date_from"]),
                    fields.Date.to_date(dates["date_to"]),
                )

            return list(
                fiscal_periods(
                    fiscal_year_dates,
                    FISCAL_MONTHS[self.period_type],
                    date_from,
                    date_to,
                )
            )
        return list(calendar_periods(self.period_type, date_from, date_to))

    def _l10n_ca_due_date(self, company, period_end, business_calendar=None):
        """Return the due date of the period ending ``period_end``.

        Fixed date: ``fixed_day`` of ``fixed_month`` in the year of the
        period end plus ``fixed_year_offset``. Otherwise the period end plus
        ``months`` (end of month kept) plus ``days``, counted as business
        days when ``business_days`` is true. The weekend and holiday rule
        applies last.
        """
        self.ensure_one()
        timing = self._l10n_ca_timing(company, period_end)
        business_calendar = business_calendar or self._l10n_ca_business_calendar(
            company
        )
        if timing.get("fixed_month"):
            due = fixed_date(
                period_end.year + int(timing.get("fixed_year_offset", 1)),
                int(timing["fixed_month"]),
                int(timing.get("fixed_day") or 31),
            )
        else:
            due = add_months(period_end, int(timing.get("months") or 0))
            days = int(timing.get("days") or 0)
            if timing.get("business_days"):
                due = business_calendar.add_business_days(due, days)
            else:
                due += timedelta(days=days)
        if self.due_date_shift == "next_business_day":
            due = business_calendar.next_business_day(due)
        return due

    def action_view_deadlines(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_ca_tax_calendar.action_l10n_ca_tax_deadline"
        )
        action["domain"] = [("rule_id", "=", self.id)]
        action["context"] = {}
        return action
