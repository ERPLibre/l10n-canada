# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ca_qc_sbd_worked_codes(self):
        """Return the worked days codes holding the scheduled hours paid.

        ``WORK100`` holds the full schedule of the contract over the
        period, leaves included: paid leaves are remunerated hours.
        """
        return {"WORK100"}

    @api.model
    def _l10n_ca_qc_sbd_unpaid_codes(self):
        """Return the worked days codes of the unpaid leave types.

        A payslip leave line carries the code of the work entry type of its
        leave type; a leave type without one gives ``GLOBAL`` and counts as
        paid. Read as superuser: only the codes are used.
        """
        leave_types = (
            self.env["hr.leave.type"]
            .sudo()
            .with_context(active_test=False)
            .search([("unpaid", "=", True)])
        )
        return set(leave_types.work_entry_type_id.mapped("code"))

    def _l10n_ca_qc_sbd_hours(self, unpaid_codes=None):
        """Return the hours paid by the payslip, before any weekly cap.

        Scheduled hours of the worked codes, less the hours of the unpaid
        leave lines; leave hours count as positive whatever the sign the
        payroll setting gives them.
        """
        self.ensure_one()
        if unpaid_codes is None:
            unpaid_codes = self._l10n_ca_qc_sbd_unpaid_codes()
        worked_codes = self._l10n_ca_qc_sbd_worked_codes()
        scheduled = unpaid = 0.0
        for line in self.worked_days_line_ids:
            if line.code in worked_codes:
                scheduled += line.number_of_hours
            elif line.code in unpaid_codes:
                unpaid += abs(line.number_of_hours)
        return max(0.0, scheduled - unpaid)
