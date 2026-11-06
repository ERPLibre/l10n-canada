# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo import api, fields, models

from ..tools import linear_ratio


class L10nCaPaidHours(models.Model):
    _name = "l10n.ca.paid.hours"
    _description = "Quebec SBD Remunerated Hours"
    _order = "date_to desc"

    @api.model
    def _default_dates(self):
        """Return the fiscal year of today, the year the estimate defaults to."""
        company = self.env.company
        return company._l10n_ca_fiscal_year(fields.Date.context_today(self))

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
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
    line_ids = fields.One2many(
        "l10n.ca.paid.hours.line", "paid_hours_id", string="Hours"
    )
    associated_hours = fields.Float(
        string="Hours of Associated Corporations",
        help="Remunerated hours of the employees of the corporations "
        "associated with the company, for their taxation years ending in "
        "this period. They count only when this year is the preceding "
        "year of the year being assessed.",
    )
    sector_exempt = fields.Boolean(
        string="Primary and Manufacturing Sectors Corporation",
        help="At least the upper ratio of the activities are primary or "
        "manufacturing sectors activities: the full Quebec small business "
        "deduction applies whatever the hours.",
    )
    primary_manufacturing_ratio = fields.Float(
        string="Primary and Manufacturing Activities (%)",
        help="Proportion of primary and manufacturing sectors activities. "
        "Between the lower and upper ratios, the deduction grows linearly.",
    )
    own_hours = fields.Float(
        string="Hours of the Company",
        compute="_compute_factor",
        help="Counted hours of the year: manual lines plus the hours "
        "brought by a payroll bridge.",
    )
    own_hours_annualized = fields.Float(
        string="Hours of the Company, Full Year",
        compute="_compute_factor",
        help="Hours of the company brought to a full year: multiplied by "
        "365 and divided by the days of the fiscal year when it has fewer "
        "than 365 days. The hours of the preceding year are not "
        "annualized.",
    )
    previous_id = fields.Many2one(
        "l10n.ca.paid.hours",
        string="Preceding Year",
        compute="_compute_factor",
    )
    previous_group_hours = fields.Float(
        string="Preceding Year, with Associated Corporations",
        compute="_compute_factor",
    )
    retained_hours = fields.Float(
        string="Hours Retained",
        compute="_compute_factor",
        help="Greater of the hours of the company in the year, brought to a "
        "full year, and the hours of the company and its associated "
        "corporations in the preceding year.",
    )
    sbd_factor = fields.Float(
        string="Quebec SBD Factor",
        compute="_compute_factor",
        digits=(16, 4),
        help="Fraction of the Quebec small business deduction rate the "
        "company is entitled to: 0 at or below the lower hours threshold, "
        "1 at or above the upper threshold, linear in between.",
    )

    _sql_constraints = [
        (
            "l10n_ca_paid_hours_unique",
            "unique (company_id, date_from)",
            "One remunerated hours record per fiscal year.",
        ),
    ]

    @api.depends("date_to")
    def _compute_name(self):
        for record in self:
            record.name = record.date_to and str(record.date_to) or ""

    def _l10n_ca_previous(self):
        self.ensure_one()
        return self.search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_to", "=", self.date_from - datetime.timedelta(days=1)),
            ],
            limit=1,
        )

    def _l10n_ca_own_hours(self):
        self.ensure_one()
        return self.company_id._l10n_ca_get_paid_hours(self.date_from, self.date_to)

    @api.depends(
        "line_ids.counted_hours",
        "associated_hours",
        "sector_exempt",
        "primary_manufacturing_ratio",
        "date_from",
        "date_to",
    )
    def _compute_factor(self):
        for record in self:
            if not (record.date_from and record.date_to and record.company_id):
                record.update(
                    {
                        "own_hours": 0.0,
                        "own_hours_annualized": 0.0,
                        "previous_id": False,
                        "previous_group_hours": 0.0,
                        "retained_hours": 0.0,
                        "sbd_factor": 0.0,
                    }
                )
                continue
            own = (
                record._l10n_ca_own_hours()
                if record.id
                else sum(record.line_ids.mapped("counted_hours"))
            )
            previous = record._l10n_ca_previous() if record.id else self.browse()
            previous_group = (
                previous._l10n_ca_own_hours() + previous.associated_hours
                if previous
                else 0.0
            )
            own_annualized = own * record._l10n_ca_annualization_ratio()
            retained = max(own_annualized, previous_group)
            record.own_hours = own
            record.own_hours_annualized = own_annualized
            record.previous_id = previous
            record.previous_group_hours = previous_group
            record.retained_hours = retained
            record.sbd_factor = record._l10n_ca_sbd_factor(retained)

    def _l10n_ca_annualization_ratio(self):
        """Return the ratio that brings the hours of the year to a full year.

        ``365 / days`` for a fiscal year of fewer than 365 days, else 1: a
        366-day year is not scaled down. Only the hours of the year itself
        are annualized, never those of the preceding year.
        """
        self.ensure_one()
        days = (self.date_to - self.date_from).days + 1
        return 365.0 / days if 0 < days < 365 else 1.0

    def _l10n_ca_sbd_factor(self, hours):
        """Return the Quebec SBD factor for ``hours`` remunerated hours.

        The thresholds are read at the first day of the fiscal year. The
        sector criterion, when it gives more, wins over the hours.
        """
        self.ensure_one()
        company = self.company_id
        day = self.date_from
        if self.sector_exempt:
            return 1.0
        hours_factor = linear_ratio(
            hours,
            company._l10n_ca_param("l10n_ca.qc_sbd.hours_lower", day),
            company._l10n_ca_param("l10n_ca.qc_sbd.hours_upper", day),
        )
        sector_factor = 0.0
        if self.primary_manufacturing_ratio:
            sector_factor = linear_ratio(
                self.primary_manufacturing_ratio / 100.0,
                company._l10n_ca_param("l10n_ca.qc_sbd.pm_ratio_lower", day),
                company._l10n_ca_param("l10n_ca.qc_sbd.pm_ratio_upper", day),
            )
        return max(hours_factor, sector_factor)


class L10nCaPaidHoursLine(models.Model):
    _name = "l10n.ca.paid.hours.line"
    _description = "Quebec SBD Remunerated Hours Line"

    paid_hours_id = fields.Many2one(
        "l10n.ca.paid.hours", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="paid_hours_id.company_id", store=True)
    source = fields.Selection(
        [
            ("employee", "Employee"),
            ("shareholder", "Majority shareholder (hours worked)"),
            ("other", "Other"),
        ],
        required=True,
        default="employee",
        help="A person holding, directly or indirectly, the majority of the "
        "voting shares counts all the hours worked to take an active part "
        "in the business, paid or not, multiplied by the shareholder hours "
        "factor; hours already counted elsewhere must not be typed again. "
        "Other people count only paid hours.",
    )
    name = fields.Char(string="Employee or Description", required=True)
    hours = fields.Float(required=True)
    weeks = fields.Float(
        help="Weeks worked. When set, the counted hours are capped at the "
        "weekly maximum times the weeks."
    )
    counted_hours = fields.Float(
        compute="_compute_counted_hours",
        store=True,
        help="Hours capped at the weekly maximum times the weeks, then, for "
        "a majority shareholder, multiplied by the shareholder hours factor.",
    )

    @api.depends(
        "hours",
        "weeks",
        "source",
        "paid_hours_id.date_from",
        "paid_hours_id.company_id",
    )
    def _compute_counted_hours(self):
        """Cap the hours at the weekly maximum, then apply the shareholder factor.

        Both parameters are read at the first day of the fiscal year. The
        cap applies to the hours worked, before the factor.
        """
        for line in self:
            hours = line.hours
            day = line.paid_hours_id.date_from
            if day:
                company = line.paid_hours_id.company_id
                if line.weeks:
                    cap = company._l10n_ca_param("l10n_ca.qc_sbd.weekly_hours_cap", day)
                    hours = min(hours, cap * line.weeks)
                if line.source == "shareholder":
                    hours *= company._l10n_ca_param(
                        "l10n_ca.qc_sbd.shareholder_hours_factor", day
                    )
            line.counted_hours = hours
