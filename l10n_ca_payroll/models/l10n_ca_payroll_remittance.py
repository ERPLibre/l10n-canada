# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import calendar
from datetime import date as Date
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

AMOUNT_FIELDS = (
    "gross_payroll",
    "cpp_employee",
    "cpp_employer",
    "cpp2_employee",
    "cpp2_employer",
    "ei_employee",
    "ei_employer",
    "income_tax",
)


def _month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _day_of_month(day, number):
    """Return ``day`` moved to day ``number`` of its month, capped at its end."""
    return day.replace(
        day=min(int(number), calendar.monthrange(day.year, day.month)[1])
    )


def _next_weekday(day):
    """Return ``day``, or the Monday after it when it falls on a weekend.

    A remittance due on a Saturday or a Sunday is on time on the next
    business day. Public holidays are not known here and do not move the
    date.
    """
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def _add_working_days(day, count):
    """Return the date ``count`` working days (Monday to Friday) after ``day``."""
    result = day
    remaining = int(count)
    while remaining > 0:
        result += timedelta(days=1)
        if result.weekday() < 5:
            remaining -= 1
    return result


class L10nCaPayrollRemittance(models.Model):
    _name = "l10n_ca.payroll.remittance"
    _description = "Payroll Source Deduction Remittance (PD7A)"
    _order = "company_id, date_from"

    name = fields.Char(compute="_compute_name", store=True)
    summary_id = fields.Many2one(
        "l10n_ca.payroll.t4.summary",
        string="Year-End Summary",
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
            ._fields["l10n_ca_payroll_remitter_type"]
            ._description_selection(self.env)
        ),
        readonly=True,
    )
    date_from = fields.Date(string="Paid From", required=True)
    date_to = fields.Date(string="Paid To", required=True)
    due_date = fields.Date(
        help="Date the CRA must receive the remittance. A due date on a "
        "Saturday or a Sunday moves to the next Monday; a due date on a "
        "public holiday moves to the next business day, which this date "
        "does not show."
    )
    payslip_count = fields.Integer(string="Payslips")
    employee_count = fields.Integer(
        string="Employees in Last Pay Period",
        help="Employees paid in the last pay period of the remittance "
        "period, added up over the payrolls of each pay frequency.",
    )
    gross_payroll = fields.Monetary()
    cpp_employee = fields.Monetary(string="CPP Employee")
    cpp_employer = fields.Monetary(string="CPP Employer")
    cpp2_employee = fields.Monetary(string="CPP2 Employee")
    cpp2_employer = fields.Monetary(string="CPP2 Employer")
    ei_employee = fields.Monetary(string="EI Employee")
    ei_employer = fields.Monetary(string="EI Employer")
    income_tax = fields.Monetary(
        help="Federal income tax, plus the provincial income tax of the "
        "provinces whose tax the CRA collects.",
    )
    total = fields.Monetary(
        string="Current Source Deductions",
        compute="_compute_total",
        store=True,
    )
    amount_paid = fields.Monetary()
    payment_date = fields.Date()

    @api.depends("date_from", "date_to")
    def _compute_name(self):
        for remittance in self:
            remittance.name = (
                f"PD7A {remittance.date_from} - {remittance.date_to}"
                if remittance.date_from and remittance.date_to
                else "PD7A"
            )

    @api.depends(*AMOUNT_FIELDS)
    def _compute_total(self):
        for remittance in self:
            remittance.total = sum(
                remittance[name] for name in AMOUNT_FIELDS if name != "gross_payroll"
            )

    @api.model
    def _l10n_ca_periods(self, company, year):
        """Return the (start, end, due date) remittance periods of ``year``.

        The periods follow the remitter type of the company. Due dates and
        split days are time parameters read at the end of each period; a
        due date on a weekend moves to the next Monday.
        """
        remitter_type = company.l10n_ca_payroll_remitter_type

        def param(key, day):
            return company._l10n_ca_param(f"l10n_ca.pd7a.{key}", day)

        periods = []
        if remitter_type == "quarterly":
            for quarter in range(4):
                start = Date(year, quarter * 3 + 1, 1)
                end = _month_end(start + relativedelta(months=2))
                due = _day_of_month(end + relativedelta(days=1), param("due_day", end))
                periods.append((start, end, _next_weekday(due)))
            return periods
        for month in range(1, 13):
            start = Date(year, month, 1)
            end = _month_end(start)
            next_month = end + relativedelta(days=1)
            if remitter_type == "accelerated_1":
                split = start.replace(day=int(param("accel1_split_day", end)))
                periods.append(
                    (
                        start,
                        split,
                        _next_weekday(
                            _day_of_month(start, param("accel1_first_due_day", end))
                        ),
                    )
                )
                periods.append(
                    (
                        split + relativedelta(days=1),
                        end,
                        _next_weekday(
                            _day_of_month(
                                next_month, param("accel1_second_due_day", end)
                            )
                        ),
                    )
                )
            elif remitter_type == "accelerated_2":
                days = param("accel2_period_end_days", end)
                working_days = param("accel2_working_days", end)
                period_start = start
                for last_day in [*sorted(int(d) for d in days), end.day]:
                    period_end = start.replace(day=last_day)
                    if period_end < period_start:
                        continue
                    periods.append(
                        (
                            period_start,
                            period_end,
                            _add_working_days(period_end, working_days),
                        )
                    )
                    period_start = period_end + relativedelta(days=1)
            else:
                due = _day_of_month(next_month, param("due_day", end))
                periods.append((start, end, _next_weekday(due)))
        return periods

    @api.model
    def _l10n_ca_generate(self, company, year, summary=None):
        """Create the remittances of ``year`` from the done payslips.

        Only periods with at least one payslip get a remittance. The
        remittances previously generated for the same summary are replaced;
        their amount paid and payment date are carried over.
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
        for start, end, due in self._l10n_ca_periods(company, year):
            slips = Payslip.search(
                [
                    ("company_id", "=", company.id),
                    ("state", "=", "done"),
                    ("l10n_ca_pay_date", ">=", start),
                    ("l10n_ca_pay_date", "<=", end),
                ]
            )
            if not slips:
                continue
            amount_paid, payment_date = paid.get((start, end), (0.0, False))
            vals = {
                "summary_id": summary.id if summary else False,
                "company_id": company.id,
                "remitter_type": company.l10n_ca_payroll_remitter_type,
                "date_from": start,
                "date_to": end,
                "due_date": due,
                "amount_paid": amount_paid,
                "payment_date": payment_date,
            }
            vals.update(slips._l10n_ca_remittance_values())
            vals_list.append(vals)
        return self.create(vals_list)
