# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import bisect
import calendar
import datetime
from collections import defaultdict

from odoo import _, api, fields, models

from ..tools import add_months, fifo_tranches, tranche_balance

PRESCRIBED_RATE = "l10n_ca.corp_tax.prescribed_rate"


class L10nCaShareholderLoan(models.Model):
    _name = "l10n.ca.shareholder.loan"
    _description = "Shareholder Loan Follow-up"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_to desc, partner_id"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    partner_id = fields.Many2one(
        "res.partner", string="Shareholder or Connected Person", required=True
    )
    date_from = fields.Date(string="Fiscal Year Start", required=True)
    date_to = fields.Date(string="Fiscal Year End", required=True)
    computed_on = fields.Date(
        string="Situation As Of",
        help="Date at which repayments were taken into account.",
    )
    opening_balance = fields.Monetary(
        help="Balance of the shareholder loan accounts at the start of the "
        "year; positive when the shareholder owes the company."
    )
    advance_amount = fields.Monetary(string="Advances")
    repayment_amount = fields.Monetary(string="Repayments")
    closing_balance = fields.Monetary()
    loan_amount = fields.Monetary(
        string="Loans Made in the Year",
        help="Advances of the year not covered by an amount the company "
        "owed the shareholder.",
    )
    deadline_date = fields.Date(
        string="Repayment Deadline",
        help="One year after the end of the fiscal year in which the loans "
        "were made (ITA s. 15(2.6)).",
    )
    unrepaid_amount = fields.Monetary(
        string="Loans of the Year Still Unpaid",
        help="Part of the loans made in the year still unpaid at the "
        "deadline, or at the situation date when the deadline is ahead.",
    )
    inclusion_amount = fields.Monetary(
        string="Amount Taxable to the Shareholder",
        help="Unpaid at the deadline: included in the shareholder's income "
        "for the year the loan was made (ITA s. 15(2)), on the T4A or "
        "T5 and RL slips.",
    )
    state = fields.Selection(
        [
            ("none", "No loan made in the year"),
            ("repaid", "Repaid in time"),
            ("at_risk", "To repay before the deadline"),
            ("included", "Taxable to the shareholder"),
        ],
        readonly=True,
        default="none",
    )
    benefit_year = fields.Integer(
        string="Benefit Calendar Year",
        help="Calendar year of the deemed interest benefit: the year of the "
        "fiscal year end.",
    )
    deemed_interest = fields.Monetary(
        string="Deemed Interest at Prescribed Rate",
        help="Prescribed rate applied day by day to the loans outstanding in "
        "the calendar year and not included in income (ITA s. 80.4(2)).",
    )
    interest_paid = fields.Monetary(
        string="Interest Paid by the Shareholder",
        help="Interest for the calendar year paid by the shareholder within "
        "30 days after its end; it reduces the benefit.",
    )
    interest_benefit = fields.Monetary(
        string="Taxable Interest Benefit",
        compute="_compute_interest_benefit",
        store=True,
    )
    note = fields.Text()

    _sql_constraints = [
        (
            "l10n_ca_shareholder_loan_unique",
            "unique (company_id, partner_id, date_from)",
            "One shareholder loan follow-up per partner and fiscal year.",
        ),
    ]

    @api.depends("partner_id", "date_to")
    def _compute_name(self):
        for record in self:
            partner = record.partner_id.display_name or ""
            record.name = f"{partner} - {record.date_to or ''}"

    @api.depends("deemed_interest", "interest_paid")
    def _compute_interest_benefit(self):
        for record in self:
            record.interest_benefit = max(
                0.0, record.deemed_interest - record.interest_paid
            )

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    @api.model
    def _l10n_ca_loan_movements(self, company):
        """Return ``{partner: [(date, debit, credit), ...]}`` sorted by date.

        Reads the posted journal items of the accounts flagged as
        shareholder loan. Items without partner cannot be attributed and
        are left out.
        """
        lines = (
            self.env["account.move.line"]
            .sudo()
            .search(
                [
                    ("company_id", "=", company.id),
                    ("account_id.l10n_ca_shareholder_loan", "=", True),
                    ("parent_state", "=", "posted"),
                    ("partner_id", "!=", False),
                ],
                order="date, id",
            )
        )
        movements = defaultdict(list)
        for line in lines:
            movements[line.partner_id].append((line.date, line.debit, line.credit))
        return movements

    @api.model
    def _l10n_ca_deadline(self, company, loan_date):
        fy_end = company._l10n_ca_fiscal_year(loan_date)[1]
        years = company._l10n_ca_param("l10n_ca.corp_tax.s15_2_repayment_years", fy_end)
        return add_months(fy_end, 12 * int(years))

    @api.model
    def _l10n_ca_included_amount(self, company, tranche, as_of):
        """Return the part of ``tranche`` included in income under s. 15(2).

        Non-zero only once the deadline has passed with an unpaid balance.
        """
        deadline = self._l10n_ca_deadline(company, tranche["date"])
        if deadline >= as_of:
            return 0.0
        return max(0.0, tranche_balance(tranche, deadline))

    @api.model
    def _l10n_ca_rate_table(self, company, year):
        """Return sorted ``(dates, rates)`` of the prescribed rate versions.

        The parameter in force on January 1 of ``year`` (company first)
        gives every version, so a rate that changes mid-quarter is
        followed day by day.
        """
        version = company._l10n_ca_param_version(
            PRESCRIBED_RATE, datetime.date(year, 1, 1)
        )
        if not version:
            # Raises the explicit missing-parameter error.
            company._l10n_ca_param(PRESCRIBED_RATE, datetime.date(year, 1, 1))
        versions = version.parameter_id.sudo().version_ids.sorted("date_from")
        return [v.date_from for v in versions], [float(v.value) for v in versions]

    @api.model
    def _l10n_ca_deemed_interest(self, company, tranches, year, as_of):
        """Return the s. 80.4(2) interest of ``year`` on ``tranches``.

        Each day weighs the balance not included under s. 15(2) by the
        prescribed rate of that day divided by the days of the year.
        """
        dates, rates = self._l10n_ca_rate_table(company, year)
        days_in_year = 366 if calendar.isleap(year) else 365
        excluded = [
            self._l10n_ca_included_amount(company, tranche, as_of)
            for tranche in tranches
        ]
        total = 0.0
        day = datetime.date(year, 1, 1)
        end = datetime.date(year, 12, 31)
        while day <= end:
            index = bisect.bisect_right(dates, day) - 1
            rate = rates[index] if index >= 0 else 0.0
            base = sum(
                max(0.0, tranche_balance(tranche, day) - excluded[i])
                for i, tranche in enumerate(tranches)
            )
            total += base * rate / days_in_year
            day += datetime.timedelta(days=1)
        return total

    @api.model
    def _l10n_ca_compute(self, company, date_from, date_to, as_of=None):
        """Create or update the follow-up of every partner for a fiscal year.

        ``as_of`` is the date of the situation (today by default):
        repayments after it are ignored for the status, so a past year can
        be reviewed as it stood. Manual fields (interest paid, note) are
        kept. Returns the follow-up records of the year.
        """
        as_of = as_of or fields.Date.context_today(self)
        currency = company.currency_id
        records = self.browse()
        for partner, movements in self._l10n_ca_loan_movements(company).items():
            movements = [m for m in movements if m[0] <= as_of]
            before = [m for m in movements if m[0] < date_from]
            during = [m for m in movements if date_from <= m[0] <= date_to]
            if not during and not sum(d - c for _d, d, c in before):
                continue
            tranches, _pool = fifo_tranches(movements)
            year_tranches = [t for t in tranches if date_from <= t["date"] <= date_to]
            deadline = self._l10n_ca_deadline(company, date_to)
            situation = min(as_of, deadline)
            unrepaid = sum(tranche_balance(t, situation) for t in year_tranches)
            loan_amount = sum(t["amount"] for t in year_tranches)
            if not year_tranches:
                state = "none"
            elif currency.is_zero(unrepaid):
                state = "repaid"
            elif deadline < as_of:
                state = "included"
            else:
                state = "at_risk"
            opening = sum(d - c for _d, d, c in before)
            advances = sum(d for _d, d, _c in during)
            repayments = sum(c for _d, _d2, c in during)
            values = {
                "computed_on": as_of,
                "opening_balance": opening,
                "advance_amount": advances,
                "repayment_amount": repayments,
                "closing_balance": opening + advances - repayments,
                "loan_amount": loan_amount,
                "deadline_date": deadline,
                "unrepaid_amount": currency.round(unrepaid),
                "inclusion_amount": (
                    currency.round(unrepaid) if state == "included" else 0.0
                ),
                "state": state,
                "benefit_year": date_to.year,
                "deemed_interest": currency.round(
                    self._l10n_ca_deemed_interest(
                        company, tranches, date_to.year, as_of
                    )
                ),
            }
            record = self.search(
                [
                    ("company_id", "=", company.id),
                    ("partner_id", "=", partner.id),
                    ("date_from", "=", date_from),
                ],
                limit=1,
            )
            if record:
                record.write(values)
            else:
                values.update(
                    company_id=company.id,
                    partner_id=partner.id,
                    date_from=date_from,
                    date_to=date_to,
                )
                record = self.create(values)
            records |= record
        return records

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------
    def _l10n_ca_schedule_reminders(self, today):
        """Create one to-do activity per loan at risk near its deadline."""
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for record in self.filtered(lambda r: r.state == "at_risk"):
            company = record.company_id
            limit = today + datetime.timedelta(
                days=company.l10n_ca_shareholder_loan_reminder_days
            )
            if record.deadline_date > limit:
                continue
            if record.activity_ids.filtered(
                lambda a, t=activity_type: a.activity_type_id == t
            ):
                continue
            user = company.l10n_ca_corporate_tax_user_id or self.env.ref(
                "base.user_admin", raise_if_not_found=False
            )
            record.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=record.deadline_date,
                summary=_("Repay the shareholder loan"),
                note=_(
                    "%(amount)s %(currency)s lent to %(partner)s in the fiscal "
                    "year ending %(year_end)s is still unpaid. Unless it is "
                    "repaid by %(deadline)s, it is taxable to the shareholder "
                    "(ITA s. 15(2)).",
                    amount=record.unrepaid_amount,
                    currency=record.currency_id.name,
                    partner=record.partner_id.display_name,
                    year_end=record.date_to,
                    deadline=record.deadline_date,
                ),
                user_id=user.id if user else self.env.uid,
            )

    @api.model
    def _cron_l10n_ca_shareholder_loans(self):
        """Refresh the current and preceding fiscal years and remind."""
        today = fields.Date.context_today(self)
        companies = self.env["res.company"].search([])
        for company in companies:
            if (
                not self.env["account.account"]
                .sudo()
                .search_count(
                    [
                        ("l10n_ca_shareholder_loan", "=", True),
                        ("company_ids", "in", company.id),
                    ],
                    limit=1,
                )
            ):
                continue
            date_from, date_to = company._l10n_ca_fiscal_year(today)
            previous_from, previous_to = company._l10n_ca_fiscal_year(
                date_from - datetime.timedelta(days=1)
            )
            records = self._l10n_ca_compute(company, date_from, date_to, today)
            records |= self._l10n_ca_compute(company, previous_from, previous_to, today)
            records._l10n_ca_schedule_reminders(today)
