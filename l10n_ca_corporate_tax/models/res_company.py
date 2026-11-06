# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_dividend_account_id = fields.Many2one(
        "account.account",
        string="Dividends Declared Account",
        check_company=True,
        help="Equity account debited when a dividend is declared "
        "(retained earnings or dividends declared).",
    )
    l10n_ca_dividend_payable_account_id = fields.Many2one(
        "account.account",
        string="Dividends Payable Account",
        check_company=True,
        help="Liability account credited at declaration and debited at "
        "payment; a reconcilable account matches both entries.",
    )
    l10n_ca_dividend_journal_id = fields.Many2one(
        "account.journal",
        string="Dividend Declaration Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
    )
    l10n_ca_grip_balance = fields.Monetary(
        string="General Rate Income Pool (GRIP)",
        currency_field="currency_id",
        help="GRIP available at the date below, from schedule 53 of the T2 "
        "return. Eligible dividends above it are excessive eligible "
        "dividend designations (Part III.1 tax).",
    )
    l10n_ca_grip_date = fields.Date(string="GRIP Balance Date")
    l10n_ca_shareholder_loan_reminder_days = fields.Integer(
        string="Shareholder Loan Reminder (days)",
        default=60,
        help="Number of days before the repayment deadline of a shareholder "
        "loan at which the scheduled action creates a to-do activity.",
    )
    # Also declared, identically, by l10n_ca_tax_calendar: neither module
    # depends on the other, and each one reads the field.
    l10n_ca_qc_instalment_frequency = fields.Selection(
        [
            ("none", "None"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
        ],
        string="Quebec Income Tax Instalments",
        help="Frequency of the Quebec corporate income tax instalments, whose "
        "quarterly conditions differ from the federal ones. Empty: the "
        "federal frequency.",
    )
    l10n_ca_corporate_tax_user_id = fields.Many2one(
        "res.users",
        string="Corporate Tax Responsible",
        help="User who receives the shareholder loan reminders. Without "
        "one, the reminders go to the administrator.",
    )

    def _l10n_ca_fiscal_year(self, day):
        """Return ``(date_from, date_to)`` of the fiscal year containing ``day``."""
        self.ensure_one()
        dates = self.compute_fiscalyear_dates(day)
        return dates["date_from"], dates["date_to"]

    def _l10n_ca_get_paid_hours(self, date_from, date_to):
        """Return the remunerated hours of the company's employees.

        Hook for the Quebec small business deduction: the base version
        sums the counted hours of the manual paid-hours records whose
        period lies within ``[date_from, date_to]``. A payroll bridge
        extends it to add the hours of its payslips.
        """
        self.ensure_one()
        records = self.env["l10n.ca.paid.hours"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", ">=", date_from),
                ("date_to", "<=", date_to),
            ]
        )
        return sum(records.mapped("line_ids.counted_hours"))
