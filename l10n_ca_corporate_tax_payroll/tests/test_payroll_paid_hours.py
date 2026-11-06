# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Remunerated hours from payslips, derived by hand.

Shipped parameters: 40 hours per week, Quebec SBD thresholds 5,000 and
5,500 hours. Payslips of the 2026 fiscal year:

- Employee A, monthly. January (31 days): 176 scheduled, 8 hours of paid
  leave, cap 40 x 31 / 7 = 177.14 -> 176. February (28 days): 160
  scheduled less 16 unpaid -> 144, cap 160. March is a draft, April is
  refunded: neither counts. A = 176 + 144 = 320.
- Employee B, weekly, March 2 to 8: a slip of 50 hours capped at 40 and a
  second slip of 40 hours for the same week; per slip 40 + 40 = 80, but
  the union of the periods is 7 days: cap 40. B = 40.
- Employee C, bi-weekly, 2025-12-29 to 2026-01-11 (14 days): 70 hours
  (cap 80). 2026 share: 11 days -> 70 x 11 / 14 = 55; 2025 share: 3 days
  -> 70 x 3 / 14 = 15.

Payroll hours of 2026: 320 + 40 + 55 = 415. With employee A flagged as
majority voting shareholder: 320 x 1.1 + 40 + 55 = 447.

A manual *Majority shareholder* line counts its hours x 1.1.
"""

from datetime import date

from odoo.tests import new_test_user, tagged

from odoo.addons.l10n_ca_corporate_tax.tests.common import L10nCaCorporateTaxCommon

from ..tools import covered_days


@tagged("post_install", "-at_install")
class TestPayrollPaidHours(L10nCaCorporateTaxCommon):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.env.ref(
            "payroll.group_payroll_manager"
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.l10n_ca_payroll_setup()
        cls.structure = cls.company.payroll_structure_id
        cls.quebec = cls.env.ref("base.state_ca_qc")
        cls.unpaid_type = cls._leave_type("Test unpaid leave", "TESTUNPAID", True)
        cls.paid_type = cls._leave_type("Test paid leave", "TESTPAID", False)
        cls.year_start = date(2026, 1, 1)
        cls.year_end = date(2026, 12, 31)

    @classmethod
    def _leave_type(cls, name, code, unpaid):
        entry_type = cls.env["hr.work.entry.type"].create({"name": name, "code": code})
        return cls.env["hr.leave.type"].create(
            {
                "name": name,
                "unpaid": unpaid,
                "requires_allocation": "no",
                "work_entry_type_id": entry_type.id,
            }
        )

    def _contract(self, name, schedule="monthly"):
        employee = self.env["hr.employee"].create(
            {"name": name, "birthday": "1985-06-15", "company_id": self.company.id}
        )
        return self.env["hr.contract"].create(
            {
                "name": f"{name} contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": 4000.0,
                "date_start": "2025-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": schedule,
                "l10n_ca_province_id": self.quebec.id,
                "journal_id": self.misc_journal.id,
            }
        )

    def _slip(self, contract, date_from, date_to, hours, done=True):
        """Create a payslip with worked days ``{code: hours}``."""
        slip = self.env["hr.payslip"].create(
            {
                "employee_id": contract.employee_id.id,
                "contract_id": contract.id,
                "struct_id": self.structure.id,
                "company_id": self.company.id,
                "date_from": date_from,
                "date_to": date_to,
                "worked_days_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": code,
                            "code": code,
                            "number_of_hours": number,
                            "contract_id": contract.id,
                        },
                    )
                    for code, number in hours.items()
                ],
            }
        )
        if done:
            slip.action_payslip_done()
        return slip

    def _payslips(self):
        employee_a = self._contract("Employee A")
        self._slip(
            employee_a,
            "2026-01-01",
            "2026-01-31",
            {"WORK100": 176.0, "TESTPAID": -8.0},
        )
        self._slip(
            employee_a,
            "2026-02-01",
            "2026-02-28",
            {"WORK100": 160.0, "TESTUNPAID": -16.0},
        )
        self._slip(employee_a, "2026-03-01", "2026-03-31", {"WORK100": 176.0}, False)
        refunded = self._slip(
            employee_a, "2026-04-01", "2026-04-30", {"WORK100": 168.0}
        )
        refunded.refund_sheet()
        employee_b = self._contract("Employee B", "weekly")
        self._slip(employee_b, "2026-03-02", "2026-03-08", {"WORK100": 50.0})
        self._slip(employee_b, "2026-03-02", "2026-03-08", {"WORK100": 40.0})
        employee_c = self._contract("Employee C", "bi-weekly")
        self._slip(employee_c, "2025-12-29", "2026-01-11", {"WORK100": 70.0})

    def _record(self, year, lines=None):
        return self.env["l10n.ca.paid.hours"].create(
            {
                "company_id": self.company.id,
                "date_from": date(year, 1, 1),
                "date_to": date(year, 12, 31),
                "line_ids": [
                    (0, 0, {"source": source, "name": source, "hours": hours})
                    for source, hours in (lines or [])
                ],
            }
        )

    def test_covered_days(self):
        self.assertEqual(
            covered_days(
                [
                    (date(2026, 1, 5), date(2026, 1, 10)),
                    (date(2026, 1, 1), date(2026, 1, 7)),
                    (date(2026, 1, 12), date(2026, 1, 12)),
                ]
            ),
            11,  # January 1 to 10, then the 12th
        )
        self.assertEqual(
            covered_days(
                [
                    (date(2026, 1, 1), date(2026, 1, 7)),
                    (date(2026, 1, 8), date(2026, 1, 14)),
                ]
            ),
            14,
        )
        self.assertEqual(covered_days([]), 0)

    def test_slip_hours(self):
        contract = self._contract("Employee D")
        slip = self._slip(
            contract,
            "2026-05-01",
            "2026-05-31",
            {"WORK100": 168.0, "TESTPAID": -8.0, "TESTUNPAID": 16.0},
            done=False,
        )
        # Paid leave stays in the schedule; unpaid hours come off whatever
        # their sign: 168 - 16 = 152.
        self.assertAlmostEqual(slip._l10n_ca_qc_sbd_hours(), 152.0)

    def test_payroll_hours_of_the_year(self):
        self._payslips()
        hours = self.company._l10n_ca_payroll_paid_hours
        self.assertAlmostEqual(hours(self.year_start, self.year_end), 415.0)
        self.assertAlmostEqual(hours(date(2025, 1, 1), date(2025, 12, 31)), 15.0)
        # The hook adds the manual lines: 415 + 100 x 1.1.
        self._record(2026, [("shareholder", 100.0)])
        self.assertAlmostEqual(
            self.company._l10n_ca_get_paid_hours(self.year_start, self.year_end),
            525.0,
        )

    def test_majority_shareholder_payslips(self):
        self._payslips()
        employee_a = self.env["hr.employee"].search(
            [("name", "=", "Employee A"), ("company_id", "=", self.company.id)]
        )
        employee_a.l10n_ca_qc_sbd_majority_shareholder = True
        self.assertAlmostEqual(
            self.company._l10n_ca_payroll_paid_hours(self.year_start, self.year_end),
            447.0,
        )

    def test_factor_and_estimate(self):
        # 2026: 415 + 4,350 shareholder hours x 1.1 = 5,200 -> (5,200 -
        # 5,000) / 500 = 0.4. The 2025 record reads the 15 hours of
        # employee C.
        self._payslips()
        previous = self._record(2025)
        record = self._record(2026, [("shareholder", 4350.0)])
        self.assertAlmostEqual(record.l10n_ca_payroll_hours, 415.0)
        self.assertAlmostEqual(record.own_hours, 5200.0)
        self.assertEqual(record.previous_id, previous)
        self.assertAlmostEqual(record.previous_group_hours, 15.0)
        self.assertAlmostEqual(record.sbd_factor, 0.4)
        estimate = self.env["l10n.ca.corporate.tax.estimate"].create(
            {
                "company_id": self.company.id,
                "date_from": self.year_start,
                "date_to": self.year_end,
            }
        )
        self.assertEqual(estimate.paid_hours_id, record)
        self.assertAlmostEqual(estimate.qc_sbd_factor, 0.4)

    def test_accountant_without_payroll_access(self):
        # The hours are read for an accountant who cannot read payslips.
        self._payslips()
        record = self._record(2026)
        accountant = new_test_user(
            self.env,
            login="ca_accountant",
            groups="account.group_account_user",
            company_id=self.company.id,
            company_ids=[(6, 0, self.company.ids)],
        )
        record.invalidate_recordset()
        self.assertAlmostEqual(record.with_user(accountant).own_hours, 415.0)
