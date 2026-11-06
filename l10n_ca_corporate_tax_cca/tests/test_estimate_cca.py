# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.tests import tagged
from odoo.tools import format_amount

from odoo.addons.l10n_ca_corporate_tax.tests.common import L10nCaCorporateTaxCommon


@tagged("post_install", "-at_install")
class TestEstimateCca(L10nCaCorporateTaxCommon):
    """Expected amounts are derived by hand; each test states its derivation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receivable = cls._account("109901", "asset_current")
        cls.revenue = cls._account("499901", "income")
        cls.Schedule = cls.env["l10n.ca.cca.schedule"]
        cls.Estimate = cls.env["l10n.ca.corporate.tax.estimate"]

    def _class(self, number):
        return self.env.ref("l10n_ca_cca.cca_class_" + number.replace(".", "_"))

    def _revenue(self, amount):
        self._entry(
            date(2026, 6, 30),
            [(self.receivable, None, amount, 0.0), (self.revenue, None, 0.0, amount)],
        )

    def _schedule(self, lines, jurisdiction="federal"):
        """Create a 2026 schedule from ``(class number, line values)`` pairs."""
        return self.Schedule.create(
            {
                "company_id": self.company.id,
                "jurisdiction": jurisdiction,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 12, 31),
                "line_ids": [
                    (0, 0, dict(values, class_id=self._class(number).id))
                    for number, values in lines
                ],
            }
        )

    def _estimate(self):
        estimate = self.Estimate.create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 12, 31),
            }
        )
        estimate.action_load_accounting()
        return estimate

    @staticmethod
    def _amounts(estimate, adjustment_type):
        return sorted(
            estimate.adjustment_ids.filtered(
                lambda line: line.auto and line.adjustment_type == adjustment_type
            ).mapped("amount")
        )

    def _depreciated_asset(self, expense_type):
        """Class 8 asset of 10,000 from 2026-01-01, 5 years straight line.

        Book: 10,000 / 5 = 2,000 posted on 2026-12-31 to an expense account
        of type ``expense_type``. Tax: RIIP 20% x 1.5 x 10,000 = 3,000.
        """
        profile = self.env["account.asset.profile"].create(
            {
                "name": "Equipment - 5 years",
                "account_asset_id": self._account("189901", "asset_fixed").id,
                "account_depreciation_id": self._account("189902", "asset_fixed").id,
                "account_expense_depreciation_id": self._account(
                    "599901", expense_type
                ).id,
                "journal_id": self.misc_journal.id,
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
                "prorata": False,
            }
        )
        asset = self.env["account.asset"].create(
            {
                "name": "Workshop equipment",
                "profile_id": profile.id,
                "purchase_value": 10000.0,
                "date_start": "2026-01-01",
                "l10n_ca_cca_class_id": self._class("8").id,
            }
        )
        asset.validate()
        asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate" and line.line_date.year == 2026
        ).create_move()
        schedule = self.Schedule.create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 12, 31),
            }
        )
        schedule.action_generate()
        self.assertAlmostEqual(schedule.total_cca, 3000.0)
        self.assertAlmostEqual(schedule.total_book_depreciation, 2000.0)
        return asset

    def test_schedule_items_loaded(self):
        # Class 8: CCA 20% x 10,000 = 2,000 claimed.
        # Class 10: 5,000 - 8,000 = -3,000, recapture 3,000; book gain 2,500.
        # Class 50: last property sold, 4,000 - 1,000 = 3,000 terminal loss;
        #   book loss 700.
        # Net: -2,000 + 3,000 - 3,000 - 2,500 + 700 = -3,800.
        # Taxable income: 100,000 - 3,800 = 96,200.
        self._revenue(100000.0)
        schedule = self._schedule(
            [
                ("8", {"opening_ucc": 10000.0, "rate": 0.2, "cca_claimed": 2000.0}),
                (
                    "10",
                    {
                        "opening_ucc": 5000.0,
                        "rate": 0.3,
                        "dispositions": 8000.0,
                        "book_gain_loss": 2500.0,
                    },
                ),
                (
                    "50",
                    {
                        "opening_ucc": 4000.0,
                        "rate": 0.55,
                        "dispositions": 1000.0,
                        "property_remaining": False,
                        "book_gain_loss": -700.0,
                    },
                ),
            ]
        )
        self.assertAlmostEqual(schedule.total_recapture, 3000.0)
        self.assertAlmostEqual(schedule.total_terminal_loss, 3000.0)
        estimate = self._estimate()
        self.assertAlmostEqual(estimate.accounting_income, 100000.0)
        self.assertEqual(
            self._amounts(estimate, "cca"), [-3000.0, -2500.0, -2000.0, 700.0, 3000.0]
        )
        self.assertAlmostEqual(estimate.taxable_income, 96200.0)
        self.assertNotIn("CCA", estimate.warning_message)
        # A second load replaces the lines instead of adding them again.
        estimate.action_load_accounting()
        self.assertEqual(len(estimate.adjustment_ids.filtered("auto")), 5)
        self.assertAlmostEqual(estimate.taxable_income, 96200.0)

    def test_quebec_schedule_and_stale_lines(self):
        # Federal: 2,000 claimed; Quebec: 1,500 claimed. Quebec taxable
        # income is 2,000 - 1,500 = 500 higher; the estimate keeps the
        # federal one: 100,000 - 2,000 = 98,000.
        self._revenue(100000.0)
        federal = self._schedule(
            [("8", {"opening_ucc": 10000.0, "rate": 0.2, "cca_claimed": 2000.0})]
        )
        self._schedule(
            [("8", {"opening_ucc": 10000.0, "rate": 0.2, "cca_claimed": 1500.0})],
            jurisdiction="quebec",
        )
        estimate = self._estimate()
        self.assertEqual(self._amounts(estimate, "cca"), [-2000.0])
        self.assertAlmostEqual(estimate.taxable_income, 98000.0)
        self.assertIn("Quebec CCA schedule", estimate.warning_message)
        # The amount follows the user's language: "500.00" or "500,00".
        self.assertIn(
            format_amount(self.env, 500.0, estimate.company_id.currency_id),
            estimate.warning_message,
        )
        self.assertNotIn("Load from Accounting again", estimate.warning_message)
        # The federal claim drops to 1,000 after the load: the estimate
        # still holds -2,000 and says so until the next load.
        federal.line_ids.cca_claimed = 1000.0
        estimate.invalidate_recordset()
        self.assertIn("Load from Accounting again", estimate.warning_message)
        estimate.action_load_accounting()
        self.assertEqual(self._amounts(estimate, "cca"), [-1000.0])
        self.assertNotIn("Load from Accounting again", estimate.warning_message)

    def test_depreciation_in_expense_account_added_back(self):
        # Accounting income 50,000 - 2,000 = 48,000; depreciation 2,000 is
        # added back by this module (the account is not of type
        # Depreciation); CCA 3,000. Taxable: 48,000 + 2,000 - 3,000 = 47,000.
        self._revenue(50000.0)
        self._depreciated_asset("expense")
        estimate = self._estimate()
        self.assertAlmostEqual(estimate.accounting_income, 48000.0)
        self.assertEqual(self._amounts(estimate, "depreciation"), [2000.0])
        self.assertEqual(self._amounts(estimate, "cca"), [-3000.0])
        self.assertAlmostEqual(estimate.taxable_income, 47000.0)

    def test_depreciation_account_added_back_once(self):
        # Same figures with an account of type Depreciation: the corporate
        # tax module adds back 2,000 and this module adds nothing more.
        self._revenue(50000.0)
        self._depreciated_asset("expense_depreciation")
        estimate = self._estimate()
        self.assertEqual(self._amounts(estimate, "depreciation"), [2000.0])
        self.assertAlmostEqual(estimate.taxable_income, 47000.0)

    def test_non_deductible_account_left_to_base(self):
        # The expense account is flagged non-deductible: the corporate tax
        # module adds back its 2,000 as a non-deductible expense, and the
        # asset depreciation is not added back a second time.
        self._revenue(50000.0)
        asset = self._depreciated_asset("expense")
        asset.profile_id.account_expense_depreciation_id.l10n_ca_tax_treatment = (
            "non_deductible"
        )
        estimate = self._estimate()
        self.assertEqual(self._amounts(estimate, "depreciation"), [])
        self.assertEqual(self._amounts(estimate, "non_deductible"), [2000.0])
        self.assertAlmostEqual(estimate.taxable_income, 47000.0)

    def test_missing_schedule_warning(self):
        self._depreciated_asset("expense")
        self.Schedule.search([("company_id", "=", self.company.id)]).unlink()
        estimate = self._estimate()
        self.assertIn("No federal CCA schedule", estimate.warning_message)
        self.assertEqual(self._amounts(estimate, "cca"), [])
