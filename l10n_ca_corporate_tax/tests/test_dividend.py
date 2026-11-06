# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import L10nCaCorporateTaxCommon


@tagged("post_install", "-at_install")
class TestDividend(L10nCaCorporateTaxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dividend_account = cls._account("329999", "equity")
        cls.payable_account = cls._account(
            "229999", "liability_payable", reconcile=True
        )
        cls.company.write(
            {
                "l10n_ca_dividend_account_id": cls.dividend_account.id,
                "l10n_ca_dividend_payable_account_id": cls.payable_account.id,
                "l10n_ca_dividend_journal_id": cls.misc_journal.id,
            }
        )
        cls.Dividend = cls.env["l10n.ca.dividend"]

    def _dividend(self, amount, kind, paid_on, partner=None, pay=True):
        dividend = self.Dividend.create(
            {
                "company_id": self.company.id,
                "partner_id": (partner or self.shareholder).id,
                "amount": amount,
                "dividend_type": kind,
                "resolution_date": paid_on,
                "payment_date": paid_on,
                "payment_journal_id": self.bank_journal.id,
            }
        )
        dividend.action_declare()
        if pay:
            dividend.action_pay()
        return dividend

    def test_entries(self):
        dividend = self._dividend(10000.0, "non_eligible", "2026-03-01")
        self.assertEqual(dividend.state, "paid")
        self.assertNotEqual(dividend.name, "/")
        payable_lines = (
            dividend.declaration_move_id.line_ids | dividend.payment_move_id.line_ids
        ).filtered(lambda line: line.account_id == self.payable_account)
        self.assertTrue(all(payable_lines.mapped("reconciled")))
        declared = dividend.declaration_move_id.line_ids.filtered(
            lambda line: line.account_id == self.dividend_account
        )
        self.assertAlmostEqual(declared.debit, 10000.0)
        dividend.action_cancel()
        self.assertEqual(dividend.state, "cancel")
        self.assertAlmostEqual(
            sum(
                self.env["account.move.line"]
                .search([("account_id", "=", self.dividend_account.id)])
                .mapped("balance")
            ),
            0.0,
        )

    def test_numbering_by_company_and_resolution_year(self):
        # The shared sequence has served another company: this company
        # still starts at 1, in the year of the resolution.
        self.env.ref("l10n_ca_corporate_tax.seq_l10n_ca_dividend").next_by_id()
        first = self._dividend(100.0, "non_eligible", "2025-12-15", pay=False)
        second = self._dividend(100.0, "non_eligible", "2026-01-15", pay=False)
        self.assertEqual(first.name, "DIV/2025/0001")
        self.assertEqual(second.name, "DIV/2026/0002")

    def test_missing_configuration(self):
        self.company.l10n_ca_dividend_account_id = False
        dividend = self.Dividend.create(
            {"partner_id": self.shareholder.id, "amount": 100.0}
        )
        with self.assertRaises(UserError):
            dividend.action_declare()

    def test_slip_boxes(self):
        # Non-eligible 10,000: box 10 = 10,000; box 11 = 10,000 x 1.15 =
        # 11,500; box 12 = 11,500 x 9.0301% = 1,038.46.
        # Eligible 5,000: box 24 = 5,000; box 25 = 5,000 x 1.38 = 6,900;
        # box 26 = 6,900 x 15.0198% = 1,036.37.
        # RL-3: A1 = 5,000, A2 = 10,000, B = 11,500 + 6,900 = 18,400,
        # C = 11,500 x 3.42% + 6,900 x 11.7% = 393.30 + 807.30 = 1,200.60.
        self._dividend(10000.0, "non_eligible", "2026-03-01")
        self._dividend(5000.0, "eligible", "2026-06-01")
        small = self.env["res.partner"].create(
            {"name": "Test Minor Holder", "l10n_ca_shareholder": True}
        )
        self._dividend(40.0, "non_eligible", "2026-07-01", partner=small)
        # Declared but unpaid: not on a slip.
        self._dividend(700.0, "non_eligible", "2026-08-01", pay=False)

        slips = self.env["l10n.ca.dividend.slip"]._l10n_ca_generate(self.company, 2026)
        slip = slips.filtered(lambda s: s.partner_id == self.shareholder)
        self.assertAlmostEqual(slip.t5_box_10, 10000.0)
        self.assertAlmostEqual(slip.t5_box_11, 11500.0)
        self.assertAlmostEqual(slip.t5_box_12, 1038.46)
        self.assertAlmostEqual(slip.t5_box_24, 5000.0)
        self.assertAlmostEqual(slip.t5_box_25, 6900.0)
        self.assertAlmostEqual(slip.t5_box_26, 1036.37)
        self.assertAlmostEqual(slip.rl3_box_a1, 5000.0)
        self.assertAlmostEqual(slip.rl3_box_a2, 10000.0)
        self.assertAlmostEqual(slip.rl3_box_b, 18400.0)
        self.assertAlmostEqual(slip.rl3_box_c, 1200.60)
        self.assertTrue(slip.t5_required)
        # 40 is below the 50 minimum of the T5 return.
        minor = slips.filtered(lambda s: s.partner_id == small)
        self.assertFalse(minor.t5_required)

        summary = slips._l10n_ca_summary()
        self.assertEqual(summary["t5_count"], 1)
        self.assertEqual(summary["rl3_count"], 2)
        self.assertAlmostEqual(summary["t5_box_10"], 10040.0)
        # 40 x 1.15 = 46 added to box 11.
        self.assertAlmostEqual(summary["t5_box_11"], 11546.0)

        wizard = self.env["l10n.ca.dividend.slip.wizard"].create(
            {"company_id": self.company.id, "year": 2026}
        )
        wizard.action_generate()
        self.assertAlmostEqual(wizard.rl3_box_b, 18446.0)
        csv_text = base64.b64decode(wizard.csv_file).decode("utf-8")
        self.assertIn("T5 box 24", csv_text.splitlines()[0])
        self.assertIn("Test Shareholder", csv_text)
        self.assertEqual(len(csv_text.strip().splitlines()), 4)  # header, 2, total

    def test_xlsx_report(self):
        self._dividend(1000.0, "eligible", "2026-03-01")
        slips = self.env["l10n.ca.dividend.slip"]._l10n_ca_generate(self.company, 2026)
        content, extension = self.env["ir.actions.report"]._render_xlsx(
            "l10n_ca_corporate_tax.report_l10n_ca_dividend_slip_xlsx", slips.ids, {}
        )
        self.assertEqual(extension, "xlsx")
        self.assertTrue(content.startswith(b"PK"))

    def test_quebec_credit_2027(self):
        # Ordinary dividend received after 2026: 2.69% of the taxable
        # amount, 11,500 x 2.69% = 309.35 (3.09% of the actual amount).
        self._dividend(10000.0, "non_eligible", "2027-01-15")
        slips = self.env["l10n.ca.dividend.slip"]._l10n_ca_generate(self.company, 2027)
        self.assertAlmostEqual(slips.rl3_box_c, 309.35)
        self.assertAlmostEqual(slips.t5_box_12, 1038.46)

    def test_grip_warning(self):
        self.company.write(
            {"l10n_ca_grip_balance": 4000.0, "l10n_ca_grip_date": date(2026, 1, 1)}
        )
        dividend = self.Dividend.create(
            {
                "company_id": self.company.id,
                "partner_id": self.shareholder.id,
                "amount": 5000.0,
                "dividend_type": "eligible",
                "resolution_date": date(2026, 6, 1),
            }
        )
        self.assertIn("GRIP", dividend.warning_message)
        dividend.amount = 3000.0
        self.assertFalse(dividend.warning_message)
        dividend.dividend_type = "non_eligible"
        dividend.amount = 50000.0
        self.assertFalse(dividend.warning_message)

    def test_dividend_refund_in_estimate(self):
        # Investment income 30,000: refundable portion 30,000 x 0.306667 =
        # 9,200.01; non-eligible dividends paid 12,000 x 0.383333 =
        # 4,600.00 is the lesser.
        self._dividend(12000.0, "non_eligible", "2026-09-01")
        estimate = self.env["l10n.ca.corporate.tax.estimate"].create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 12, 31),
                "accounting_income": 30000.0,
                "investment_income": 30000.0,
            }
        )
        self.assertAlmostEqual(estimate.non_eligible_dividends_paid, 12000.0)
        self.assertAlmostEqual(estimate.nerdtoh_addition, 9200.01)
        self.assertAlmostEqual(estimate.dividend_refund, 4600.0)

    def test_shareholder_flag_visible_to_invoicing_administrator(self):
        # Without the full accounting features, the administrator of
        # Invoicing holds group_account_manager alone: the shareholder flag
        # must still be on the partner form, since the dividend recipient
        # is chosen among flagged partners.
        admin = self.env["res.users"].create(
            {
                "name": "Invoicing Administrator",
                "login": "l10n_ca_invoicing_admin",
                "company_id": self.company.id,
                "company_ids": [(6, 0, self.company.ids)],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_manager").id,
                        ],
                    )
                ],
            }
        )
        self.assertFalse(admin.has_group("account.group_account_readonly"))
        arch = (
            self.env["res.partner"]
            .with_user(admin)
            .get_views([(False, "form")])["views"]["form"]["arch"]
        )
        self.assertIn('name="l10n_ca_shareholder"', arch)
