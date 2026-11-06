# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import defaultdict

from odoo import models

from ..tools import covered_days


class ResCompany(models.Model):
    _inherit = "res.company"

    def _l10n_ca_get_paid_hours(self, date_from, date_to):
        """Add the payroll hours to the hours of the manual records."""
        hours = super()._l10n_ca_get_paid_hours(date_from, date_to)
        return hours + self._l10n_ca_payroll_paid_hours(date_from, date_to)

    def _l10n_ca_payroll_paid_hours(self, date_from, date_to):
        """Return the counted hours of the done payslips in ``[date_from, date_to]``.

        Each payslip gives its paid hours (``hr.payslip._l10n_ca_qc_sbd_hours``)
        capped at the weekly maximum times its number of weeks, then
        prorated by the days of its period inside the range. Per employee,
        the total is capped again at the weekly maximum times the weeks
        covered by the union of the payslip periods, so a second payslip of
        the same period (a bonus, a correction) adds no hours beyond the
        cap. Refunded payslips and their refunds are left out. The capped
        hours of an employee flagged as majority voting shareholder are
        multiplied by the ``l10n_ca.qc_sbd.shareholder_hours_factor``
        parameter, as for a manual *Majority shareholder* line.

        Both parameters are read at ``date_from``, as for the manual lines. The payslips
        are read as superuser: only aggregated hours leave this method.
        """
        self.ensure_one()
        slips = (
            self.env["hr.payslip"]
            .sudo()
            .search(
                [
                    ("company_id", "=", self.id),
                    ("state", "=", "done"),
                    ("credit_note", "=", False),
                    ("refunded_id", "=", False),
                    ("date_from", "<=", date_to),
                    ("date_to", ">=", date_from),
                ]
            )
        )
        if not slips:
            return 0.0
        weekly_cap = self._l10n_ca_param("l10n_ca.qc_sbd.weekly_hours_cap", date_from)
        unpaid_codes = slips._l10n_ca_qc_sbd_unpaid_codes()
        hours_by_employee = defaultdict(float)
        periods_by_employee = defaultdict(list)
        for slip in slips:
            period_days = (slip.date_to - slip.date_from).days + 1
            start = max(slip.date_from, date_from)
            end = min(slip.date_to, date_to)
            hours = min(
                slip._l10n_ca_qc_sbd_hours(unpaid_codes),
                weekly_cap * period_days / 7.0,
            )
            hours_by_employee[slip.employee_id] += (
                hours * ((end - start).days + 1) / period_days
            )
            periods_by_employee[slip.employee_id].append((start, end))
        shareholder_factor = self._l10n_ca_param(
            "l10n_ca.qc_sbd.shareholder_hours_factor", date_from
        )
        return sum(
            min(hours, weekly_cap * covered_days(periods_by_employee[employee]) / 7.0)
            * (
                shareholder_factor
                if employee.l10n_ca_qc_sbd_majority_shareholder
                else 1.0
            )
            for employee, hours in hours_by_employee.items()
        )
