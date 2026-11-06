# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import calendar
from datetime import date as Date
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import float_round

AMOUNT_FIELDS = ("qpp", "qpip", "income_tax", "hsf", "cnesst")

# Revenu Quebec frequency used when the company leaves it empty: the one
# that matches its CRA remitter type, monthly without one.
FEDERAL_TO_QC_FREQUENCY = {
    "quarterly": "quarterly",
    "regular": "monthly",
    "accelerated_1": "twice_monthly",
    "accelerated_2": "weekly",
}


def _month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _day_of_month(day, number):
    """Return ``day`` moved to day ``number`` of its month, capped at its end."""
    return day.replace(
        day=min(int(number), calendar.monthrange(day.year, day.month)[1])
    )


def _is_business_day(day, closed):
    """Return whether ``day`` is neither a weekend day nor in ``closed``."""
    return day.weekday() < 5 and day not in closed


def _next_business_day(day, closed):
    """Return ``day``, or the first business day after it.

    A payment due on a Saturday, a Sunday or a day of ``closed`` (public
    holiday, Revenu Quebec closure) is on time on the next business day
    (TP-1015.G part 11.3).
    """
    while not _is_business_day(day, closed):
        day += timedelta(days=1)
    return day


def _add_business_days(day, count, closed):
    """Return the date ``count`` business days after ``day``.

    Saturdays, Sundays and the days of ``closed`` are not counted.
    """
    result = day
    remaining = int(count)
    while remaining > 0:
        result += timedelta(days=1)
        if _is_business_day(result, closed):
            remaining -= 1
    return result


class L10nCaQcPayrollRemittance(models.Model):
    _name = "l10n_ca.qc.payroll.remittance"
    _description = "Revenu Quebec Remittance of Source Deductions (TPZ-1015.R.14)"
    _order = "company_id, date_from"

    name = fields.Char(compute="_compute_name", store=True)
    summary_id = fields.Many2one(
        "l10n_ca.qc.rl1.summary",
        string="RL-1 Summary",
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    remitter_type = fields.Selection(
        selection=lambda self: (
            self.env["res.company"]
            ._fields["l10n_ca_qc_remitter_type"]
            ._description_selection(self.env)
        ),
        string="Remittance Frequency",
        readonly=True,
    )
    date_from = fields.Date(string="Paid From", required=True)
    date_to = fields.Date(string="Paid To", required=True)
    due_date = fields.Date(
        help="Date Revenu Quebec must receive the remittance. A due date "
        "on a Saturday, a Sunday or a non-business day moves to the next "
        "business day; weekly due dates count business days. The Quebec "
        "public holidays and the Revenu Quebec closure days are known when "
        "the Tax Compliance Calendar module is installed; without it, only "
        "Saturdays and Sundays are not business days."
    )
    payslip_count = fields.Integer(string="Payslips")
    employee_count = fields.Integer(string="Employees")
    gross_payroll = fields.Monetary()
    qpp = fields.Monetary(
        string="QPP",
        help="Employee and employer QPP contributions, second additional "
        "contributions included (column B of the RL-1 summary).",
    )
    qpip = fields.Monetary(
        string="QPIP",
        help="Employee and employer QPIP premiums (column C).",
    )
    income_tax = fields.Monetary(
        string="Quebec Income Tax", help="Quebec income tax withheld (column D)."
    )
    hsf = fields.Monetary(
        string="Health Services Fund",
        help="Health Services Fund (column E). With the new employer basis, "
        "the rate is the one of the total payroll paid from January 1 to "
        "the end of the period, applied to the subject salaries of the "
        "period.",
    )
    cnesst = fields.Monetary(
        string="CNESST",
        help="Periodic payment of the occupational health and safety "
        "premium, entered in the CNESST box of the remittance slip.",
    )
    total = fields.Monetary(compute="_compute_total", store=True)
    amount_paid = fields.Monetary()
    payment_date = fields.Date()

    @api.depends("date_from", "date_to")
    def _compute_name(self):
        for remittance in self:
            remittance.name = (
                f"TPZ-1015.R.14 {remittance.date_from} - {remittance.date_to}"
                if remittance.date_from and remittance.date_to
                else "TPZ-1015.R.14"
            )

    @api.depends(*AMOUNT_FIELDS)
    def _compute_total(self):
        for remittance in self:
            remittance.total = sum(remittance[name] for name in AMOUNT_FIELDS)

    @api.model
    def _l10n_ca_qc_frequency(self, company):
        """Return the remittance frequency of ``company`` at Revenu Quebec."""
        return company.l10n_ca_qc_remitter_type or FEDERAL_TO_QC_FREQUENCY.get(
            company.l10n_ca_payroll_remitter_type, "monthly"
        )

    @api.model
    def _l10n_ca_qc_closed_days(self, company, year):
        """Return the dates of ``year`` that are not business days, weekends aside.

        They are the Quebec public holidays and the days the Revenu Quebec
        offices are closed (TP-1015.G part 11.3), read from the holidays of
        jurisdiction ``quebec_payroll`` of the Tax Compliance Calendar
        module (``res.company._l10n_ca_holidays``). Without that module the
        set is empty and only Saturdays and Sundays move a due date.
        """
        if not hasattr(company, "_l10n_ca_holidays"):
            return set()
        return set(company._l10n_ca_holidays("quebec_payroll", year))

    @api.model
    def _l10n_ca_qc_next_business_day(self, company, day):
        """Return ``day``, or the first business day after it, for ``company``."""
        closed = self._l10n_ca_qc_closed_days(
            company, day.year
        ) | self._l10n_ca_qc_closed_days(company, day.year + 1)
        return _next_business_day(day, closed)

    @api.model
    def _l10n_ca_qc_period_end(self, company, day):
        """Return the last day of the remittance period holding ``day``."""
        for start, end, _due in self._l10n_ca_qc_periods(company, day.year):
            if start <= day <= end:
                return end
        return Date(day.year, 12, 31)

    @api.model
    def _l10n_ca_qc_periods(self, company, year):
        """Return the (start, end, due date) remittance periods of ``year``.

        The periods follow the Revenu Quebec frequency of the company
        (TP-1015.G table 7); due days are time parameters read at the end
        of each period, and a due date that is not a business day moves to
        the next business day. Weekly due dates count business days. The
        annual period is due on the due day of the month after the year.
        Without a frequency, the company follows the one that matches its
        CRA remitter type.
        """
        frequency = self._l10n_ca_qc_frequency(company)
        closed = self._l10n_ca_qc_closed_days(
            company, year
        ) | self._l10n_ca_qc_closed_days(company, year + 1)

        def shift(day):
            return _next_business_day(day, closed)

        def param(key, day):
            return company._l10n_ca_param(f"l10n_ca.qc.remittance.{key}", day)

        periods = []
        if frequency == "annual":
            end = Date(year, 12, 31)
            due = _day_of_month(end + relativedelta(days=1), param("due_day", end))
            return [(Date(year, 1, 1), end, shift(due))]
        if frequency == "quarterly":
            for quarter in range(4):
                start = Date(year, quarter * 3 + 1, 1)
                end = _month_end(start + relativedelta(months=2))
                due = _day_of_month(end + relativedelta(days=1), param("due_day", end))
                periods.append((start, end, shift(due)))
            return periods
        for month in range(1, 13):
            start = Date(year, month, 1)
            end = _month_end(start)
            next_month = end + relativedelta(days=1)
            if frequency == "twice_monthly":
                split = start.replace(day=int(param("twice_monthly_split_day", end)))
                periods.append(
                    (
                        start,
                        split,
                        shift(
                            _day_of_month(
                                start, param("twice_monthly_first_due_day", end)
                            )
                        ),
                    )
                )
                periods.append(
                    (
                        split + relativedelta(days=1),
                        end,
                        shift(
                            _day_of_month(
                                next_month, param("twice_monthly_second_due_day", end)
                            )
                        ),
                    )
                )
            elif frequency == "weekly":
                days = param("weekly_period_end_days", end)
                working_days = param("weekly_working_days", end)
                period_start = start
                for last_day in [*sorted(int(d) for d in days), end.day]:
                    period_end = start.replace(day=last_day)
                    if period_end < period_start:
                        continue
                    periods.append(
                        (
                            period_start,
                            period_end,
                            _add_business_days(period_end, working_days, closed),
                        )
                    )
                    period_start = period_end + relativedelta(days=1)
            else:
                due = _day_of_month(next_month, param("due_day", end))
                periods.append((start, end, shift(due)))
        return periods

    @api.model
    def _l10n_ca_qc_period_hsf(self, company, year, end, slips):
        """Return the HSF of a remittance period with the new employer basis.

        The rate is the one of the total payroll paid from January 1 to
        ``end``: the done payslips of the company, all provinces, plus the
        payroll of the associated employers entered on the company
        (TP-1015.G part 6.5). It applies to the salaries of ``slips``, the
        Quebec payslips of the period, subject to the contribution.
        """
        paid = self.env["hr.payslip"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "done"),
                ("l10n_ca_pay_date", ">=", Date(year, 1, 1)),
                ("l10n_ca_pay_date", "<=", end),
            ]
        )
        total_payroll = (
            paid._l10n_ca_line_totals()["GROSS"] + company.l10n_ca_qc_associated_payroll
        )
        rate = company._l10n_ca_qc_hsf_rate(total_payroll, end)
        salary = slips._l10n_ca_line_totals()["CA_QC_SAL"]
        return float_round(salary * rate / 100, precision_digits=2)

    @api.model
    def _l10n_ca_qc_generate(self, company, year, summary=None):
        """Create the remittances of ``year`` from the done payslips.

        Only periods with a payslip of an employment in Quebec get a
        remittance. The remittances previously generated for the same
        summary are replaced; their amount paid and payment date are kept.
        With the new employer basis, the HSF of each period is computed on
        the period by ``_l10n_ca_qc_period_hsf``; the payslips hold the
        HSF accrued at the rate known when they were computed.
        """
        previous = self.search(
            [
                ("company_id", "=", company.id),
                ("summary_id", "=", summary.id if summary else False),
                ("date_from", ">=", Date(year, 1, 1)),
                ("date_to", "<=", Date(year, 12, 31)),
            ]
        )
        paid = {
            (r.date_from, r.date_to): (r.amount_paid, r.payment_date) for r in previous
        }
        previous.unlink()
        Payslip = self.env["hr.payslip"]
        vals_list = []
        for start, end, due in self._l10n_ca_qc_periods(company, year):
            slips = Payslip.search(
                [
                    ("company_id", "=", company.id),
                    ("state", "=", "done"),
                    ("l10n_ca_pay_date", ">=", start),
                    ("l10n_ca_pay_date", "<=", end),
                    ("l10n_ca_province_id.code", "=", "QC"),
                ]
            )
            if not slips:
                continue
            amount_paid, payment_date = paid.get((start, end), (0.0, False))
            vals = {
                "summary_id": summary.id if summary else False,
                "company_id": company.id,
                "remitter_type": self._l10n_ca_qc_frequency(company),
                "date_from": start,
                "date_to": end,
                "due_date": due,
                "amount_paid": amount_paid,
                "payment_date": payment_date,
            }
            vals.update(slips._l10n_ca_qc_remittance_values())
            if company.l10n_ca_qc_hsf_basis == "year_to_date":
                vals["hsf"] = self._l10n_ca_qc_period_hsf(company, year, end, slips)
            vals_list.append(vals)
        return self.create(vals_list)
