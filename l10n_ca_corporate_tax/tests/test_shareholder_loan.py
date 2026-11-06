# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.tests import tagged

from ..tools import add_months, fifo_tranches, tranche_balance
from .common import L10nCaCorporateTaxCommon


@tagged("post_install", "-at_install")
class TestShareholderLoan(L10nCaCorporateTaxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loan_account = cls._account(
            "113399", "asset_current", l10n_ca_shareholder_loan=True
        )
        cls.cash = cls.bank_journal.default_account_id
        cls.Loan = cls.env["l10n.ca.shareholder.loan"]

    def _lend(self, day, amount):
        self._entry(
            day,
            [
                (self.loan_account, self.shareholder, amount, 0.0),
                (self.cash, None, 0.0, amount),
            ],
        )

    def _repay(self, day, amount):
        self._entry(
            day,
            [
                (self.cash, None, amount, 0.0),
                (self.loan_account, self.shareholder, 0.0, amount),
            ],
        )

    def _compute(self, year, as_of):
        records = self.Loan._l10n_ca_compute(
            self.company, date(year, 1, 1), date(year, 12, 31), as_of
        )
        return records.filtered(lambda r: r.partner_id == self.shareholder)

    def test_deadline_and_inclusion(self):
        # 10,000 lent on 2025-03-15, 4,000 repaid on 2026-06-30. The
        # deadline is one year after the 2025 year end: 2026-12-31.
        self._lend("2025-03-15", 10000.0)
        self._repay("2026-06-30", 4000.0)

        before = self._compute(2025, date(2026, 10, 26))
        self.assertEqual(before.deadline_date, date(2026, 12, 31))
        self.assertEqual(before.state, "at_risk")
        self.assertAlmostEqual(before.loan_amount, 10000.0)
        self.assertAlmostEqual(before.unrepaid_amount, 6000.0)
        self.assertAlmostEqual(before.inclusion_amount, 0.0)

        after = self._compute(2025, date(2027, 1, 15))
        self.assertEqual(after, before, "the follow-up is updated, not duplicated")
        self.assertEqual(after.state, "included")
        self.assertAlmostEqual(after.inclusion_amount, 6000.0)

        following = self._compute(2026, date(2027, 1, 15))
        self.assertAlmostEqual(following.opening_balance, 10000.0)
        self.assertAlmostEqual(following.repayment_amount, 4000.0)
        self.assertAlmostEqual(following.closing_balance, 6000.0)
        self.assertEqual(following.state, "none")

    def test_repaid_on_deadline_day(self):
        self._lend("2025-11-01", 5000.0)
        self._repay("2026-12-31", 5000.0)
        record = self._compute(2025, date(2027, 2, 1))
        self.assertEqual(record.state, "repaid")
        self.assertAlmostEqual(record.inclusion_amount, 0.0)

    def test_repaid_one_day_late(self):
        self._lend("2025-11-01", 5000.0)
        self._repay("2027-01-01", 5000.0)
        record = self._compute(2025, date(2027, 2, 1))
        self.assertEqual(record.state, "included")
        self.assertAlmostEqual(record.inclusion_amount, 5000.0)

    def test_deemed_interest(self):
        # 10,000 outstanding from 2025-03-15 to 2025-12-31.
        # Prescribed rate: 4% in Q1-Q2 2025, 3% in Q3-Q4 2025.
        # Days at 4%: 17 (Mar 15-31) + 91 (Apr-Jun) = 108; at 3%: 184.
        # 10,000 x (0.04 x 108 + 0.03 x 184) / 365 = 10,000 x 9.84 / 365
        # = 269.59.
        self._lend("2025-03-15", 10000.0)
        self._repay("2026-06-30", 4000.0)
        record = self._compute(2025, date(2026, 10, 26))
        self.assertAlmostEqual(record.deemed_interest, 269.59, places=2)
        record.interest_paid = 50.0
        self.assertAlmostEqual(record.interest_benefit, 219.59, places=2)
        # Once 6,000 is included under s. 15(2), only the 4,000 repaid in
        # time bears the deemed interest: 4,000 x 9.84 / 365 = 107.84.
        record = self._compute(2025, date(2027, 1, 15))
        self.assertAlmostEqual(record.deemed_interest, 107.84, places=2)

    def test_deemed_interest_2024(self):
        # 10,000 outstanding all of 2024 (366 days). Prescribed rate: 6%
        # in Q1-Q2 (91 + 91 days), 5% in Q3-Q4 (92 + 92 days).
        # 10,000 x (0.06 x 182 + 0.05 x 184) / 366 = 201,200 / 366
        # = 549.73.
        self._lend("2024-01-01", 10000.0)
        record = self._compute(2024, date(2025, 6, 1))
        self.assertEqual(record.deadline_date, date(2025, 12, 31))
        self.assertAlmostEqual(record.deemed_interest, 549.73, places=2)

    def test_reminder_activity(self):
        self._lend("2025-06-01", 2000.0)
        records = self._compute(2025, date(2026, 11, 15))
        records._l10n_ca_schedule_reminders(date(2026, 11, 15))
        self.assertEqual(len(records.activity_ids), 1)
        self.assertEqual(records.activity_ids.date_deadline, date(2026, 12, 31))
        records._l10n_ca_schedule_reminders(date(2026, 11, 16))
        self.assertEqual(len(records.activity_ids), 1, "no duplicate reminder")

    def test_reminder_too_early(self):
        self._lend("2025-06-01", 2000.0)
        records = self._compute(2025, date(2026, 6, 1))
        records._l10n_ca_schedule_reminders(date(2026, 6, 1))
        self.assertFalse(records.activity_ids)

    def test_wizard_and_cron(self):
        self._lend("2025-06-01", 2000.0)
        wizard = self.env["l10n.ca.shareholder.loan.wizard"].create(
            {
                "company_id": self.company.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 12, 31),
                "as_of": date(2026, 3, 1),
            }
        )
        action = wizard.action_compute()
        record = self.Loan.search(action["domain"])
        self.assertEqual(record.partner_id, self.shareholder)
        self.assertEqual(record.state, "at_risk")
        # The cron refreshes the current and preceding fiscal years of
        # today; it must run whatever today is.
        self.Loan._cron_l10n_ca_shareholder_loans()

    def test_fifo_and_credit_pool(self):
        # The company owes 3,000: a 5,000 advance is a 2,000 loan.
        tranches, pool = fifo_tranches(
            [
                (date(2025, 1, 10), 0.0, 3000.0),
                (date(2025, 2, 1), 5000.0, 0.0),
                (date(2025, 3, 1), 1000.0, 0.0),
                (date(2025, 4, 1), 0.0, 2500.0),
            ]
        )
        self.assertEqual(pool, 0.0)
        self.assertEqual([t["amount"] for t in tranches], [2000.0, 1000.0])
        # The repayment settles the oldest tranche first.
        self.assertEqual(tranche_balance(tranches[0]), 0.0)
        self.assertEqual(tranche_balance(tranches[1]), 500.0)
        self.assertEqual(tranche_balance(tranches[1], date(2025, 3, 31)), 1000.0)

    def test_add_months(self):
        self.assertEqual(add_months(date(2025, 12, 31), 2), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 6, 30), 2), date(2026, 8, 31))
        self.assertEqual(add_months(date(2026, 6, 15), 2), date(2026, 8, 15))
