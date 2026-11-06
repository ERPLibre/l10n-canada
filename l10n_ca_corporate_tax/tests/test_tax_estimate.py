# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.tests import tagged

from .common import L10nCaCorporateTaxCommon


@tagged("post_install", "-at_install")
class TestTaxEstimate(L10nCaCorporateTaxCommon):
    def _estimate(self, year=2026, **values):
        values.setdefault("accounting_income", 100000.0)
        values.update(
            company_id=self.company.id,
            date_from=date(year, 1, 1),
            date_to=date(year, 12, 31),
        )
        return self.env["l10n.ca.corporate.tax.estimate"].create(values)

    def _hours(self, year, hours):
        return self.env["l10n.ca.paid.hours"].create(
            {
                "company_id": self.company.id,
                "date_from": date(year, 1, 1),
                "date_to": date(year, 12, 31),
                "line_ids": [(0, 0, {"name": "Employees", "hours": hours})],
            }
        )

    def test_active_income_without_quebec_sbd(self):
        # Federal: 100,000 x (38% - 10% - 19%) = 9,000.
        # Quebec, no remunerated hours record: factor 0, 100,000 x 11.5%.
        estimate = self._estimate()
        self.assertAlmostEqual(estimate.taxable_income, 100000.0)
        self.assertAlmostEqual(estimate.sbd_income, 100000.0)
        self.assertAlmostEqual(estimate.fed_base_tax, 38000.0)
        self.assertAlmostEqual(estimate.fed_abatement, 10000.0)
        self.assertAlmostEqual(estimate.fed_sbd, 19000.0)
        self.assertAlmostEqual(estimate.fed_general_reduction, 0.0)
        self.assertAlmostEqual(estimate.federal_tax, 9000.0)
        self.assertEqual(estimate.qc_sbd_factor, 0.0)
        self.assertAlmostEqual(estimate.quebec_tax, 11500.0)
        self.assertAlmostEqual(estimate.total_tax, 20500.0)
        self.assertIn("estimate", estimate.warning_message)

    def test_active_income_with_quebec_sbd(self):
        # 5,600 hours: factor 1. Year starting 2026-01-01 (before the
        # April 29, 2026 change): 11.5% - 8.3% = 3.2% -> 3,200.
        self._hours(2026, 5600.0)
        estimate = self._estimate()
        self.assertEqual(estimate.qc_sbd_factor, 1.0)
        self.assertAlmostEqual(estimate.qc_sbd_rate, 0.083)
        self.assertAlmostEqual(estimate.qc_sbd, 8300.0)
        self.assertAlmostEqual(estimate.quebec_tax, 3200.0)
        self.assertAlmostEqual(estimate.total_tax, 12200.0)

    def test_quebec_sbd_partial_and_next_rate(self):
        # 5,250 hours: factor 0.5 -> 11,500 - 0.5 x 8,300 = 7,350.
        self._hours(2026, 5250.0)
        self.assertAlmostEqual(self._estimate().quebec_tax, 7350.0)
        # Year starting 2027-01-01 (after April 29, 2026): SBD rate 9.3%,
        # full factor -> 11,500 - 9,300 = 2,200.
        self._hours(2027, 5600.0)
        estimate = self._estimate(2027)
        self.assertAlmostEqual(estimate.qc_sbd_rate, 0.093)
        self.assertAlmostEqual(estimate.quebec_tax, 2200.0)

    def test_passive_income_grind(self):
        # Preceding-year AAII 100,000: reduction 500,000 x 5 x 50,000 /
        # 500,000 = 250,000. Income 600,000: 250,000 at 9% (22,500) and
        # 350,000 at 15% (52,500) = 75,000.
        estimate = self._estimate(accounting_income=600000.0, previous_aaii=100000.0)
        self.assertAlmostEqual(estimate.business_limit_reduction, 250000.0)
        # The same grind applies to the Quebec limit.
        self.assertAlmostEqual(estimate.qc_business_limit, 250000.0)
        self.assertAlmostEqual(estimate.sbd_income, 250000.0)
        self.assertAlmostEqual(estimate.fed_general_reduction, 45500.0)
        self.assertAlmostEqual(estimate.federal_tax, 75000.0)
        # At 150,000 of AAII the business limit is nil: 600,000 x 15%.
        estimate.previous_aaii = 150000.0
        self.assertAlmostEqual(estimate.reduced_business_limit, 0.0)
        self.assertAlmostEqual(estimate.federal_tax, 90000.0)

    def test_taxable_capital_grind(self):
        # Taxable capital 30M: (30M - 10M) / (50M - 10M) = 50% of 500,000.
        estimate = self._estimate(taxable_capital=30000000.0)
        self.assertAlmostEqual(estimate.reduced_business_limit, 250000.0)
        estimate.taxable_capital = 50000000.0
        self.assertAlmostEqual(estimate.reduced_business_limit, 0.0)
        # No SBD: 100,000 x 15% = 15,000.
        self.assertAlmostEqual(estimate.federal_tax, 15000.0)

    def test_short_year_quebec_business_limit(self):
        # 2026-07-01 to 2026-12-31: 184 days, under 51 weeks. Both limits:
        # 500,000 x 184 / 365 = 252,054.79 (CO-771 line 80). Hours: 2,800
        # x 365 / 184 = 5,554.35, full factor. Rate of a year starting
        # after April 29, 2026: 9.3%. Quebec SBD 252,054.79 x 9.3% =
        # 23,441.10; Quebec tax 400,000 x 11.5% - 23,441.10 = 22,558.90.
        self.env["l10n.ca.paid.hours"].create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 7, 1),
                "date_to": date(2026, 12, 31),
                "line_ids": [(0, 0, {"name": "Employees", "hours": 2800.0})],
            }
        )
        estimate = self.env["l10n.ca.corporate.tax.estimate"].create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 7, 1),
                "date_to": date(2026, 12, 31),
                "accounting_income": 400000.0,
            }
        )
        self.assertAlmostEqual(estimate.business_limit, 252054.79)
        self.assertAlmostEqual(estimate.qc_business_limit, 252054.79)
        self.assertEqual(estimate.qc_sbd_factor, 1.0)
        self.assertAlmostEqual(estimate.qc_sbd, 23441.10)
        self.assertAlmostEqual(estimate.quebec_tax, 22558.90)

    def test_quebec_paid_up_capital_grind(self):
        # Quebec grinds on paid-up capital (CO-771 amount J): 30M gives
        # (30M - 10M) / 40M = 50% of 500,000 = 250,000, while the federal
        # limit, without taxable capital, stays 500,000. Quebec SBD
        # 250,000 x 8.3% = 20,750.
        self._hours(2026, 5600.0)
        estimate = self._estimate(
            accounting_income=400000.0, previous_qc_paid_up_capital=30000000.0
        )
        self.assertAlmostEqual(estimate.reduced_business_limit, 500000.0)
        self.assertAlmostEqual(estimate.qc_business_limit, 250000.0)
        self.assertAlmostEqual(estimate.qc_sbd, 20750.0)
        # J = 12M: (12M - 10M) / 40M = 5%, 475,000. The federal taxable
        # capital of 30M grinds only the federal limit.
        estimate.write(
            {"taxable_capital": 30000000.0, "previous_qc_paid_up_capital": 12000000.0}
        )
        self.assertAlmostEqual(estimate.reduced_business_limit, 250000.0)
        self.assertAlmostEqual(estimate.qc_business_limit, 475000.0)
        # Paid-up capital not entered: the taxable capital stands for it.
        estimate.previous_qc_paid_up_capital = 0.0
        self.assertAlmostEqual(estimate.qc_business_limit, 250000.0)

    def test_investment_income(self):
        # 50,000 of investment income only: 38% - 10% + 10 2/3% (0.106667)
        # = 19,000 - 5,000 + 5,333.35 = 19,333.35; refundable 30 2/3%
        # (0.306667) = 15,333.35.
        estimate = self._estimate(accounting_income=50000.0, investment_income=50000.0)
        self.assertAlmostEqual(estimate.active_income, 0.0)
        self.assertAlmostEqual(estimate.federal_tax, 19333.35)
        self.assertAlmostEqual(estimate.nerdtoh_addition, 15333.35)
        self.assertAlmostEqual(estimate.quebec_tax, 5750.0)

    def test_psb_income(self):
        # 100,000 PSB income: 38% - 10% + 5% = 33,000.
        estimate = self._estimate(psb_income=100000.0)
        self.assertAlmostEqual(estimate.sbd_income, 0.0)
        self.assertAlmostEqual(estimate.federal_tax, 33000.0)

    def test_zero_and_loss(self):
        estimate = self._estimate(accounting_income=-5000.0)
        self.assertEqual(estimate.taxable_income, 0.0)
        self.assertEqual(estimate.total_tax, 0.0)
        self.assertFalse(estimate.fed_instalments_required)

    def test_deadlines_and_instalments(self):
        # Small CCPC with the SBD: federal balance 3 months after
        # 2026-12-31, Quebec 2 months, returns 6 months.
        self._hours(2026, 5600.0)
        estimate = self._estimate(
            previous_federal_tax=8000.0, previous_quebec_tax=4000.0
        )
        self.assertEqual(estimate.fed_balance_due_date, date(2027, 3, 31))
        self.assertEqual(estimate.qc_balance_due_date, date(2027, 2, 28))
        self.assertEqual(estimate.filing_due_date, date(2027, 6, 30))
        self.assertEqual(estimate.instalment_frequency, "quarterly")
        self.assertEqual(estimate.qc_instalment_frequency, "quarterly")
        self.assertTrue(estimate.fed_instalments_required)
        self.assertTrue(estimate.qc_instalments_required)
        estimate.action_compute_instalments()
        federal = estimate.instalment_ids.filtered(
            lambda i: i.jurisdiction == "federal"
        )
        quebec = estimate.instalment_ids.filtered(lambda i: i.jurisdiction == "quebec")
        # Federal: lesser of 9,000 and 8,000 / 4 = 2,000 at each quarter end.
        self.assertEqual(
            federal.mapped("date"),
            [
                date(2026, 3, 31),
                date(2026, 6, 30),
                date(2026, 9, 30),
                date(2026, 12, 31),
            ],
        )
        self.assertEqual(federal.mapped("amount"), [2000.0] * 4)
        # Quebec: lesser of 3,200 and 4,000 / 4 = 800.
        self.assertEqual(quebec.mapped("amount"), [800.0] * 4)

    def test_balance_due_sbd_claimed_preceding_year(self):
        # Investment income only: no SBD in the year. The SBD claimed in
        # the preceding year, with a preceding taxable income within the
        # business limit, still gives the three-month federal delay.
        estimate = self._estimate(
            accounting_income=50000.0,
            investment_income=50000.0,
            previous_taxable_income=100000.0,
        )
        self.assertAlmostEqual(estimate.sbd_income, 0.0)
        self.assertEqual(estimate.fed_balance_due_date, date(2027, 2, 28))
        estimate.previous_sbd_claimed = True
        self.assertEqual(estimate.fed_balance_due_date, date(2027, 3, 31))
        self.assertEqual(estimate.qc_balance_due_date, date(2027, 2, 28))
        # Preceding taxable income above the business limit: two months.
        estimate.previous_taxable_income = 600000.0
        self.assertEqual(estimate.fed_balance_due_date, date(2027, 2, 28))

    def test_monthly_and_below_threshold(self):
        # Without the SBD in the year nor the preceding year, the
        # small-CCPC test fails: monthly. No federal SBD: 15,000.
        estimate = self._estimate(
            taxable_capital=50000000.0,
            previous_federal_tax=12000.0,
            previous_quebec_tax=2500.0,
        )
        self.assertEqual(estimate.instalment_frequency, "monthly")
        self.assertEqual(estimate.fed_balance_due_date, date(2027, 2, 28))
        # Quebec preceding-year tax below 3,000: no Quebec instalment.
        self.assertFalse(estimate.qc_instalments_required)
        estimate.action_compute_instalments()
        self.assertEqual(len(estimate.instalment_ids), 12)
        self.assertEqual(estimate.instalment_ids[0].date, date(2026, 1, 31))
        self.assertEqual(estimate.instalment_ids[1].date, date(2026, 2, 28))
        # 12,000 / 12 = 1,000 (lesser of 15,000 and 12,000).
        self.assertEqual(sum(estimate.instalment_ids.mapped("amount")), 12000.0)

    def test_quebec_quarterly_without_federal_sbd(self):
        # Associated company with no share of the business limit: no
        # federal SBD, so monthly federal instalments. Quebec asks for
        # income from a qualifying business, not for the SBD: quarterly.
        # Federal: 100,000 x 15% = 15,000; Quebec: 100,000 x 11.5% = 11,500.
        estimate = self._estimate(
            business_limit_allocation=0.0,
            previous_federal_tax=20000.0,
            previous_quebec_tax=12000.0,
        )
        self.assertAlmostEqual(estimate.sbd_income, 0.0)
        self.assertAlmostEqual(estimate.federal_tax, 15000.0)
        self.assertAlmostEqual(estimate.quebec_tax, 11500.0)
        self.assertEqual(estimate.instalment_frequency, "monthly")
        self.assertEqual(estimate.qc_instalment_frequency, "quarterly")
        estimate.action_compute_instalments()
        federal = estimate.instalment_ids.filtered(
            lambda i: i.jurisdiction == "federal"
        )
        quebec = estimate.instalment_ids.filtered(lambda i: i.jurisdiction == "quebec")
        # Federal: lesser of 15,000 and 20,000 / 12 = 1,250 each month.
        self.assertEqual(len(federal), 12)
        self.assertEqual(federal.mapped("amount"), [1250.0] * 12)
        # Quebec: lesser of 11,500 and 12,000 / 4 = 2,875 each quarter.
        self.assertEqual(
            quebec.mapped("date"),
            [
                date(2026, 3, 31),
                date(2026, 6, 30),
                date(2026, 9, 30),
                date(2026, 12, 31),
            ],
        )
        self.assertEqual(quebec.mapped("amount"), [2875.0] * 4)
        # A Quebec profile of its own: monthly Quebec instalments.
        self.company.l10n_ca_qc_instalment_frequency = "monthly"
        self.assertEqual(estimate.qc_instalment_frequency, "monthly")
        self.assertEqual(estimate.instalment_frequency, "monthly")

    def test_quebec_quarterly_conditions(self):
        self.company.l10n_ca_qc_instalment_frequency = "quarterly"
        estimate = self._estimate(
            qc_paid_up_capital=12000000.0, previous_qc_paid_up_capital=11000000.0
        )
        # Paid-up capital above 10 million in both years: monthly.
        self.assertEqual(estimate.qc_instalment_frequency, "monthly")
        self.assertIn("quarterly Quebec instalments", estimate.warning_message)
        # The preceding year at 10 million or less is enough.
        estimate.previous_qc_paid_up_capital = 10000000.0
        self.assertEqual(estimate.qc_instalment_frequency, "quarterly")
        self.assertNotIn("quarterly Quebec instalments", estimate.warning_message)
        # Taxable income of the associated group above 500,000 in both
        # years: monthly in both jurisdictions.
        estimate.write(
            {"group_taxable_income": 600000.0, "previous_taxable_income": 500001.0}
        )
        self.assertEqual(estimate.instalment_frequency, "monthly")
        self.assertEqual(estimate.qc_instalment_frequency, "monthly")
        estimate.previous_taxable_income = 500000.0
        self.assertEqual(estimate.instalment_frequency, "quarterly")
        self.assertEqual(estimate.qc_instalment_frequency, "quarterly")
        # Tax obligations not met in the last 12 months: monthly.
        estimate.tax_obligations_met = False
        self.assertEqual(estimate.instalment_frequency, "monthly")
        self.assertEqual(estimate.qc_instalment_frequency, "monthly")

    def test_quebec_quarterly_business_income(self):
        # Investment income only: no qualifying business income in the
        # year. Quarterly in Quebec once the preceding year had some.
        estimate = self._estimate(accounting_income=50000.0, investment_income=50000.0)
        self.assertAlmostEqual(estimate.active_income, 0.0)
        self.assertEqual(estimate.qc_instalment_frequency, "monthly")
        estimate.previous_business_income = True
        self.assertEqual(estimate.qc_instalment_frequency, "quarterly")
        self.assertEqual(estimate.instalment_frequency, "monthly")

    def test_load_from_accounting(self):
        # Revenue 120,000, meals 4,000: accounting income 116,000, half of
        # the meals added back: taxable income 118,000.
        revenue = self._account("419999", "income")
        meals = self._account("599999", "expense", l10n_ca_tax_treatment="meals")
        cash = self.bank_journal.default_account_id
        self._entry(
            "2026-05-01",
            [(cash, None, 120000.0, 0.0), (revenue, None, 0.0, 120000.0)],
        )
        self._entry(
            "2026-05-02",
            [(meals, None, 4000.0, 0.0), (cash, None, 0.0, 4000.0)],
        )
        estimate = self._estimate(accounting_income=0.0)
        estimate.write(
            {
                "adjustment_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Manual CCA",
                            "adjustment_type": "cca",
                            "amount": -1000.0,
                        },
                    )
                ]
            }
        )
        estimate.action_load_accounting()
        self.assertAlmostEqual(estimate.accounting_income, 116000.0)
        auto = estimate.adjustment_ids.filtered("auto")
        self.assertEqual(auto.adjustment_type, "meals")
        self.assertAlmostEqual(auto.amount, 2000.0)
        self.assertAlmostEqual(estimate.taxable_income, 117000.0)
        estimate.action_load_accounting()
        self.assertEqual(len(estimate.adjustment_ids), 2, "auto lines replaced")
