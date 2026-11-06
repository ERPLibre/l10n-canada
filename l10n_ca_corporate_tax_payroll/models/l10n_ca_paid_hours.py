# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class L10nCaPaidHours(models.Model):
    _inherit = "l10n.ca.paid.hours"

    l10n_ca_payroll_hours = fields.Float(
        string="Hours from Payroll",
        compute="_compute_l10n_ca_payroll_hours",
        help="Counted hours of the done payslips of the fiscal year, "
        "capped at the weekly maximum per employee. They are included in "
        "the hours of the company: the manual lines only add the hours not "
        "paid through payroll.",
    )

    @api.depends("company_id", "date_from", "date_to")
    def _compute_l10n_ca_payroll_hours(self):
        for record in self:
            record.l10n_ca_payroll_hours = (
                record.company_id._l10n_ca_payroll_paid_hours(
                    record.date_from, record.date_to
                )
                if record.company_id and record.date_from and record.date_to
                else 0.0
            )


class L10nCaPaidHoursLine(models.Model):
    _inherit = "l10n.ca.paid.hours.line"

    source = fields.Selection(
        help="A person holding, directly or indirectly, the majority of the "
        "voting shares counts all the hours worked to take an active part "
        "in the business, paid or not, multiplied by the shareholder hours "
        "factor. The hours paid through payroll already count with that "
        "factor when the employee is flagged as majority voting "
        "shareholder: a manual line holds only the hours worked without "
        "pay. Other people count only paid hours.",
    )
