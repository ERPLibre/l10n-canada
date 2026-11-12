# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""British Columbia payslips checked against the T4127 formulas (option 1)
and the step-by-step examples of the T4032 for British Columbia, January
and July 2026.

Shipped parameters used by the derivations:

- brackets 7.70% from 50,363 / 10.50% from 100,728 / 12.29% from 115,648 /
  14.70% from 140,430 / 16.80% from 190,405 / 20.50% from 265,545, the
  first one at 5.06% from January 1, 2026 (KP of the second bracket
  1,330), 6.14% from July 1, 2026 (KP 786) and 5.60% from 2027 (KP 1,058);
- basic personal amount 13,216: K1P = 0.0506 x 13,216 = 668.73 in January,
  0.0614 x 13,216 = 811.46 from July;
- BC tax reduction: S2 575 from January 2026, 805 from July 2026, 690 from
  2027; threshold 25,570; rate 3.56%; maximum income 41,722 from January
  2026, 44,952 from July 2026;
- Employer Health Tax: exemption 1,000,000 up to a total remuneration of
  1,500,000; 5.85% up to 1,500,000, 1.95% above; charities 1,500,000 up to
  4,500,000, 2.925% up to 4,500,000, 1.95% above;
- WorkSafeBC maximum assessable earnings 127,500 (2027: 130,800).

The federal amounts are those of the tests of l10n_ca_payroll: at 5,000 a
month, C = 280.15, EI = 81.50, A = 59,435.04, T1 = 5,338.29 and 444.86 of
federal tax. K2P = lowest rate x (min(P x C x 0.0495 / 0.0595, 3,519.45) +
min(P x EI, 1,123.07)); at 5,000 a month the bracket is 3,774.79.
"""

from datetime import date
from functools import partial
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page
from odoo.addons.l10n_ca_payroll.tools.watch import PageChanged

from ..watch import worksafebc_maximum


@tagged("post_install", "-at_install")
class TestBritishColumbiaPayroll(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.env.ref(
            "payroll.group_payroll_manager"
        )

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ca")
    def setUpClass(cls):
        super().setUpClass()
        # Assertions read the English messages whatever languages the
        # database has loaded.
        cls.env = cls.env(context=dict(cls.env.context, lang="en_US"))
        cls.company = cls.env.company
        cls.company.l10n_ca_payroll_setup()
        cls.structure = cls.company.payroll_structure_id
        cls.british_columbia = cls.env.ref("base.state_ca_bc")
        cls.journal = cls.company_data["default_journal_misc"]
        # Total British Columbia remuneration of 500,000: in the exemption,
        # no Employer Health Tax; no WorkSafeBC rate.
        cls.account = cls.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": cls.company.id,
                "province_id": cls.british_columbia.id,
                "employer_tax_previous_payroll": 500000.0,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "British Columbia Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "British Columbia Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.british_columbia.id,
                "journal_id": self.journal.id,
                **vals,
            }
        )

    def _account(self, **vals):
        self.account.write(vals)
        return self.account

    def _slip(self, contract, date_from, date_to, done=False, bonus=0.0):
        inputs = []
        if bonus:
            inputs.append(
                (
                    0,
                    0,
                    {
                        "name": "Bonus",
                        "code": "CA_BONUS",
                        "amount": bonus,
                        "contract_id": contract.id,
                    },
                )
            )
        slip = self.env["hr.payslip"].create(
            {
                "employee_id": contract.employee_id.id,
                "contract_id": contract.id,
                "struct_id": self.structure.id,
                "company_id": self.company.id,
                "date_from": date_from,
                "date_to": date_to,
                "input_line_ids": inputs,
            }
        )
        slip.compute_sheet()
        if done:
            slip.action_payslip_done()
        return slip

    def _monthly_slips(self, contract, months):
        return [
            self._slip(contract, date(2026, month, 1), date(2026, month, 28), True)
            for month in months
        ]

    @staticmethod
    def _line(slip, code):
        return sum(
            slip.line_ids.filtered(lambda line: line.code == code).mapped("total")
        )

    def _assert_lines(self, slip, expected):
        for code, amount in expected.items():
            self.assertAlmostEqual(self._line(slip, code), amount, places=2, msg=code)

    # ------------------------------------------------------------------
    # Set-up
    # ------------------------------------------------------------------

    def test_setup_rules_and_accounts(self):
        codes = set(self.structure.rule_ids.mapped("code"))
        self.assertTrue(
            {"CA_BC_SAL", "CA_BC_WCB_IE", "CA_BC_ER_TAX", "CA_BC_WCB"} <= codes
        )
        for xmlid in ("rule_bc_employer_tax", "rule_bc_wcb"):
            rule = self.env.ref(f"l10n_ca_bc_payroll.{xmlid}").with_company(
                self.company
            )
            self.assertEqual(rule.account_debit.code, "512121")
            self.assertEqual(rule.account_credit.code, "221206")
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)
        account = self._account()
        self.assertTrue(account.has_employer_tax)

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        self.assertTrue(contract.l10n_ca_prov_computed)
        self.assertEqual(contract.l10n_ca_prov_bpa, 13216.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,435.04 > 50,363 -> V 0.077, KP 1,330; S = 0 (A > 41,722)
        #   K2P = 0.0506 x 3,774.79 = 191.00
        #   T4 = 0.077 x 59,435.04 - 1,330 - 668.73 - 191.00 = 2,386.76
        # (5,338.29 + 2,386.76) / 12 = 643.75, of which 444.86 federal and
        # 198.89 British Columbia.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -198.89,
                "CA_BC_SAL": 5000.0,
                "CA_BC_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("BC", tax_line.name)
        # 5,000 of the remuneration of 500,000 is in the exemption: no
        # Employer Health Tax line; no WorkSafeBC rate, no premium line.
        codes = slip.line_ids.mapped("code")
        self.assertNotIn("CA_BC_ER_TAX", codes)
        self.assertNotIn("CA_BC_WCB", codes)
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 643.75)

    def test_monthly_5000_july(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-07-01", "2026-07-31")
        # Rates of July 1, 2026: V 0.077, KP 786, lowest rate 0.0614.
        #   K2P = 0.0614 x 3,774.79 = 231.77
        #   T4 = 0.077 x 59,435.04 - 786 - 811.4624 - 231.7722 = 2,747.2635
        # The total sits near the half cent: T1 unrounded is 12,184.1832 -
        # 3,804 - 2,303.28 - 528.4708 - 210.14 = 5,338.2924, and
        # (5,338.2924 + 2,747.2635) / 12 = 673.7963 -> 673.80, of which
        # 444.86 federal and 228.94 British Columbia.
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -228.94})
        self.assertFalse(slip.l10n_ca_warning)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for British Columbia, January
        2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84. The CRA gives 5,957.85
        of federal tax and 2,620.47 of British Columbia tax for the year
        (0.0770 x 62,798.84 - 1,330 - 885.04, no reduction): 8,578.32 / 52
        = 164.97, of which 114.57 federal.
        """
        # 5,633.33 x 12 / 52 = 1,300.00 a week.
        contract = self._contract(
            5633.33, schedule_pay="weekly", l10n_ca_rrsp_amount=80.0
        )
        slip = self._slip(contract, "2026-03-02", "2026-03-08")
        self._assert_lines(
            slip,
            {
                "BASIC": 1300.0,
                "CA_CPP": -73.35,
                "CA_EI": -21.19,
                "CA_FIT": -114.57,
                "CA_PIT": -50.40,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for British Columbia: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872. The CRA gives 9,406.39 federal and
        3,916.50 British Columbia (0.077 x 79,872 - 1,330 - 903.64) for the
        year: 13,322.89 / 52 = 256.21, of which 180.89 federal.
        """
        # 6,933.33 x 12 / 52 = 1,600.00 a week.
        contract = self._contract(6933.33, schedule_pay="weekly")
        # A first pay of 76,000 reaches both maximums and bears 56 of CPP2.
        self._slip(contract, "2026-01-05", "2026-01-11", done=True, bonus=74400.0)
        slip = self._slip(contract, "2026-01-12", "2026-01-18")
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": -64.0,
                "CA_EI": 0.0,
                "CA_FIT": -180.89,
                "CA_PIT": -75.32,
            },
        )

    def test_t4032_july_example_below_ympe(self):
        """Example of the T4032 for British Columbia effective July 1, 2026.

        Same pay as in January, paid in July: 0.0770 x 62,798.84 - 786 -
        1,101.88 (0.0614 x the credits) = 2,975.57 for the year, no
        reduction (A > 44,952). (5,957.85 + 2,975.57) / 52 = 171.80, of
        which 114.57 federal and 57.23 British Columbia.
        """
        contract = self._contract(
            5633.33, schedule_pay="weekly", l10n_ca_rrsp_amount=80.0
        )
        slip = self._slip(contract, "2026-07-06", "2026-07-12")
        self._assert_lines(
            slip,
            {
                "BASIC": 1300.0,
                "CA_CPP": -73.35,
                "CA_EI": -21.19,
                "CA_FIT": -114.57,
                "CA_PIT": -57.23,
            },
        )

    def test_t4032_july_example_above_ympe(self):
        """Second example of the T4032 effective July 1, 2026: 1,600 a week.

        0.077 x 79,872 - 786 - 1,096.51 (0.0614 x the credits) = 4,267.63:
        (9,406.39 + 4,267.63) / 52 = 262.96, of which 180.89 federal and
        82.07 British Columbia.
        """
        contract = self._contract(6933.33, schedule_pay="weekly")
        self._slip(contract, "2026-07-06", "2026-07-12", done=True, bonus=74400.0)
        slip = self._slip(contract, "2026-07-13", "2026-07-19")
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": -64.0,
                "CA_EI": 0.0,
                "CA_FIT": -180.89,
                "CA_PIT": -82.07,
            },
        )

    def test_tax_reduction_zones(self):
        """Factor S in its three zones, for each version of the amounts."""
        Payslip = self.env["hr.payslip"]

        def reduction(day, income, tax):
            vals = {"company": self.company, "date": day}
            return Payslip._l10n_ca_prov_reduction(vals, "l10n_ca.bc", income, tax)

        january, july, next_year = date(2026, 3, 1), date(2026, 7, 1), date(2027, 3, 1)
        # A at most 25,570: the lesser of T4 and S2.
        self.assertAlmostEqual(reduction(january, 20000, 1000), 575.0)
        self.assertAlmostEqual(reduction(january, 20000, 300), 300.0)
        self.assertAlmostEqual(reduction(july, 25570, 1000), 805.0)
        self.assertAlmostEqual(reduction(next_year, 20000, 1000), 690.0)
        # Above 25,570: S2 - (30,000 - 25,570) x 3.56% = S2 - 157.708.
        self.assertAlmostEqual(reduction(january, 30000, 1000), 417.292)
        self.assertAlmostEqual(reduction(january, 30000, 100), 100.0)
        self.assertAlmostEqual(reduction(july, 30000, 1000), 647.292)
        self.assertAlmostEqual(reduction(next_year, 30000, 1000), 532.292)
        # 575 - 16,152 x 3.56% = -0.01 at the January maximum: at least 0.
        self.assertEqual(reduction(january, 41722, 1000), 0.0)
        # July: 805 - 19,382 x 3.56% = 115.00 at 44,952, then 0.
        self.assertAlmostEqual(reduction(july, 44952, 1000), 115.0008)
        self.assertEqual(reduction(july, 44952.01, 1000), 0.0)
        self.assertEqual(reduction(january, 41722.01, 1000), 0.0)
        # Another province is left to the engine.
        vals = {"company": self.company, "date": january}
        self.assertEqual(
            Payslip._l10n_ca_prov_reduction(vals, "l10n_ca.xx", 20000, 1000), 0.0
        )

    def test_tax_reduction_on_payslips(self):
        # 2,000 a month: C = 0.0595 x (2,000 - 3,500 / 12) = 101.65, F5A =
        # 101.65 x 0.01 / 0.0595 = 17.08, EI = 32.60;
        # A = 12 x (2,000 - 17.08) = 23,795.04 <= 25,570 (first zone).
        #   K2P = 0.0506 x (12 x 101.65 x 0.0495 / 0.0595 + 12 x 32.60) = 71.14
        #   T4 = 0.0506 x 23,795.04 - 668.73 - 71.14 = 464.16
        #   S = min(464.16, 575) = 464.16: T2 = 0, no British Columbia tax.
        contract = self._contract(2000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        vals = slip._l10n_ca_compute(contract, 2000.0)
        self.assertAlmostEqual(vals["provincial_annual_income"], 23795.04)
        self.assertAlmostEqual(vals["provincial_basic_tax"], 464.16, places=2)
        self.assertAlmostEqual(vals["provincial_reduction"], 464.16, places=2)
        self.assertAlmostEqual(vals["provincial_annual_tax"], 0.0)
        self._assert_lines(slip, {"CA_PIT": 0.0})
        # 3,000 a month: C = 161.15, F5A = 27.08, EI = 48.90;
        # A = 12 x (3,000 - 27.08) = 35,675.04, between 25,570 and 41,722.
        #   K2P = 0.0506 x (12 x 161.15 x 0.0495 / 0.0595 + 12 x 48.90)
        #       = 111.10
        #   T4 = 0.0506 x 35,675.04 - 668.73 - 111.10 = 1,025.33
        #   S = 575 - (35,675.04 - 25,570) x 3.56% = 215.26; T2 = 810.07
        contract = self._contract(3000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        vals = slip._l10n_ca_compute(contract, 3000.0)
        self.assertAlmostEqual(vals["provincial_annual_income"], 35675.04)
        self.assertAlmostEqual(vals["provincial_basic_tax"], 1025.33, places=2)
        self.assertAlmostEqual(vals["provincial_reduction"], 215.26, places=2)
        self.assertAlmostEqual(vals["provincial_annual_tax"], 810.07, places=2)
        # Paid in July: T4 = 0.0614 x 35,675.04 - 811.46 - 134.81
        # (0.0614 x the same K2P base) = 1,244.18; S = 805 - 359.74 =
        # 445.26; T2 = 798.92.
        slip = self._slip(contract, "2026-07-01", "2026-07-31")
        vals = slip._l10n_ca_compute(contract, 3000.0)
        self.assertAlmostEqual(vals["provincial_basic_tax"], 1244.18, places=2)
        self.assertAlmostEqual(vals["provincial_reduction"], 445.26, places=2)
        self.assertAlmostEqual(vals["provincial_annual_tax"], 798.92, places=2)

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1BC claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.077 x 59,435.04 - 1,330 - 191.00 - 120 = 2,935.49
        # (5,338.29 + 2,935.49) / 12 = 689.48 -> 689.48 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -264.62})

    def test_2027_parameters(self):
        param = self.company._l10n_ca_param
        day = date(2027, 6, 1)
        brackets = param("l10n_ca.bc.brackets", day)
        self.assertEqual(brackets[0], [0, 0.056])
        self.assertEqual(
            brackets[1:], param("l10n_ca.bc.brackets", date(2026, 7, 1))[1:]
        )
        self.assertEqual(param("l10n_ca.bc.bpa", day), 13216)
        self.assertEqual(param("l10n_ca.bc.tax_reduction_basic", day), 690)
        self.assertEqual(param("l10n_ca.bc.tax_reduction_threshold", day), 25570)
        self.assertEqual(param("l10n_ca.bc.tax_reduction_max_income", day), 44952)

    # ------------------------------------------------------------------
    # Employer Health Tax
    # ------------------------------------------------------------------

    def test_employer_tax_rate_selection(self):
        account = self._account()
        day = date(2026, 6, 30)
        rate = partial(account._l10n_ca_employer_tax_rate, self.company, "l10n_ca.bc")
        exemption = partial(
            account._l10n_ca_employer_tax_exemption, self.company, "l10n_ca.bc"
        )
        self.assertEqual(rate(0.0, day), 0.0585)
        self.assertEqual(rate(1500000, day), 0.0585)
        self.assertEqual(rate(1500000.01, day), 0.0195)
        self.assertEqual(exemption(1500000, day), 1000000)
        self.assertEqual(exemption(1500000.01, day), 0.0)
        account.employer_tax_charity = True
        self.assertEqual(rate(4500000, day), 0.02925)
        self.assertEqual(rate(4500000.01, day), 0.0195)
        self.assertEqual(exemption(4500000, day), 1500000)
        self.assertEqual(exemption(4500000.01, day), 0.0)
        # An associated employer takes its allocated share of the regular
        # exemption, at most 1,000,000.
        account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 1200000,
            }
        )
        self.assertEqual(rate(1200000, day), 0.0585)
        self.assertEqual(exemption(1200000, day), 1000000)
        account.employer_tax_eligible = False
        self.assertEqual(exemption(1200000, day), 0.0)
        account.employer_tax_associated = False
        self.assertEqual(exemption(1200000, day), 0.0)

    def test_employer_tax_notch(self):
        # Total remuneration 1,200,000, in the notch: rate 5.85% above the
        # exemption of 1,000,000. January 600,000 stays in the exemption;
        # February brings R to 1,200,000: 5.85% x 200,000 = 11,700, the
        # tax of the year 5.85% x (1,200,000 - 1,000,000).
        self._account(employer_tax_previous_payroll=1200000.0)
        contract = self._contract(600000.0)
        january, february = self._monthly_slips(contract, (1, 2))
        self._assert_lines(january, {"CA_BC_ER_TAX": 0.0, "CA_BC_SAL": 600000.0})
        self.assertNotIn("CA_BC_ER_TAX", january.line_ids.mapped("code"))
        self._assert_lines(february, {"CA_BC_ER_TAX": 11700.0})
        line = february.line_ids.filtered(lambda line: line.code == "CA_BC_ER_TAX")
        self.assertRegex(line.name, r"^British Columbia Employer Health Tax \(5[.,]85")

    def test_employer_tax_above_the_notch(self):
        # Total remuneration 1,800,000 > 1,500,000: no exemption, 1.95% of
        # each pay; three pays of 600,000 bear 3 x 11,700 = 35,100 = 1.95%
        # x 1,800,000.
        self._account(employer_tax_previous_payroll=1800000.0)
        contract = self._contract(600000.0)
        slips = self._monthly_slips(contract, (1, 2, 3))
        self.assertEqual([self._line(s, "CA_BC_ER_TAX") for s in slips], [11700.0] * 3)

    def test_employer_tax_across_the_exemption(self):
        self._account(
            employer_tax_associated=True,
            employer_tax_allocated_exemption=12000.0,
            employer_tax_basis="estimate",
            employer_tax_estimated_payroll=1200000.0,
        )
        contract = self._contract(5000.0)
        january, february, march, april = self._monthly_slips(contract, (1, 2, 3, 4))
        # Group remuneration 1,200,000: rate 5.85%, allocated exemption
        # 12,000. January 5,000 and February 10,000 cumulative: under it.
        # March: 15,000 - 12,000 = 3,000 x 5.85% = 175.50
        # April: the whole 5,000 x 5.85% = 292.50
        self._assert_lines(january, {"CA_BC_ER_TAX": 0.0})
        self._assert_lines(february, {"CA_BC_ER_TAX": 0.0})
        self._assert_lines(march, {"CA_BC_ER_TAX": 175.50})
        self._assert_lines(april, {"CA_BC_ER_TAX": 292.50})

    def test_employer_tax_charity(self):
        # A charity with 2,500,000 of remuneration: exemption 1,500,000 and
        # 2.925%. Five pays of 500,000: the first three use the exemption,
        # the last two bear 500,000 x 2.925% = 14,625 each; 29,250 for the
        # year, (2,500,000 - 1,500,000) x 2.925%.
        self._account(
            employer_tax_charity=True,
            employer_tax_basis="estimate",
            employer_tax_estimated_payroll=2500000.0,
        )
        contract = self._contract(500000.0)
        slips = self._monthly_slips(contract, range(1, 6))
        self.assertEqual(
            [self._line(s, "CA_BC_ER_TAX") for s in slips],
            [0.0, 0.0, 0.0, 14625.0, 14625.0],
        )

    # ------------------------------------------------------------------
    # WorkSafeBC
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self._account(wcb_rate=1.55)
        contract = self._contract(15000.0)
        slips = self._monthly_slips(contract, range(1, 11))
        # 15,000 a month up to 127,500: August reaches 120,000, September
        # takes the 7,500 left, October nothing.
        self.assertEqual(
            [self._line(s, "CA_BC_WCB_IE") for s in slips],
            [15000.0] * 8 + [7500.0, 0.0],
        )
        # 15,000 x 1.55 / 100 = 232.50; 7,500 x 1.55 / 100 = 116.25
        self._assert_lines(slips[0], {"CA_BC_WCB": 232.50})
        self._assert_lines(slips[8], {"CA_BC_WCB": 116.25})
        self.assertNotIn("CA_BC_WCB", slips[9].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_BC_WCB")
        self.assertEqual(wcb.name, "WorkSafeBC Premium")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(15000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_BC_WCB_IE": 0.0, "CA_BC_WCB": 0.0})

    def test_wcb_2027_maximum(self):
        param = self.company._l10n_ca_param
        self.assertEqual(
            param("l10n_ca.bc.wcb.max_insurable", date(2026, 6, 1)), 127500
        )
        self.assertEqual(
            param("l10n_ca.bc.wcb.max_insurable", date(2027, 6, 1)), 130800
        )

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    _WAGE_RATES_PAGE = (
        "<html><body><p>The maximum wage rate for 2027, effective January 1, "
        "2027, is $130,800.00.</p><h3>2026 Maximum Wage Rate</h3><p>The June "
        "2, 2025, President's Approval set the 2026 Maximum Wage Rate amount "
        "at $127,500.00, effective January 1, 2026.</p></body></html>"
    )

    def test_worksafebc_page_reader(self):
        page = self._WAGE_RATES_PAGE.encode()
        self.assertEqual(
            worksafebc_maximum(page, 2026), {"l10n_ca.bc.wcb.max_insurable": 127500.0}
        )
        self.assertEqual(
            worksafebc_maximum(page, 2027), {"l10n_ca.bc.wcb.max_insurable": 130800.0}
        )
        self.assertIsNone(worksafebc_maximum(page, 2028))
        with self.assertRaises(PageChanged):
            worksafebc_maximum(b"<html><body><p>Moved.</p></body></html>", 2026)

    @freeze_time("2026-11-15")
    def test_watcher_of_the_worksafebc_page(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_bc_payroll.source_worksafebc_maximum")
        page = self._WAGE_RATES_PAGE.encode()

        def fetch(self_, url, probe=False):
            return 200, page

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # Both years on the page match the shipped versions.
        self.assertEqual(source.watch_state, "ok")
        self.assertIn(
            "l10n_ca.bc.wcb.max_insurable = 127500.0: matches.", source.watch_message
        )
        self.assertIn(
            "l10n_ca.bc.wcb.max_insurable = 130800.0: matches.", source.watch_message
        )

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.bc.%")]
        )
        self.assertTrue(parameters)
        self.assertFalse(
            parameters - sources.parameter_ids, "parameters without an official source"
        )
        module_dir = Path(__file__).resolve().parents[1]
        self.assertEqual(
            (module_dir / sources_page.PAGE_FILE).read_text(encoding="utf-8"),
            sources_page.render(module_dir),
            "static/description/sources.html is out of date: run "
            "l10n_ca_payroll/tools/sources_page.py",
        )
