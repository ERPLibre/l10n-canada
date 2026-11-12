# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Ontario payslips checked against the T4127 formulas (option 1).

Shipped 2026 parameters used by the derivations: CPP 5.95% (base 4.95%)
up to 74,600, exemption 3,500 (291.66 a month), base CPP maximum 3,519.45;
EI 1.63% up to 68,900 (maximum 1,123.07). Ontario: brackets 5.05% /
9.15% from 53,891 (KP 2,210) / 11.16% from 107,785 (KP 4,376) / 12.16%
from 150,000 (KP 5,876) / 13.16% from 220,000 (KP 8,076); basic personal
amount 12,989 (K1P = 0.0505 x 12,989 = 655.94); surtax 20% above 5,818
and 36% above 7,446; tax reduction 300 plus 554 per dependant; Ontario
Health Premium 600 for an A from 48,600 to 72,000 and 750 from 72,600 to
200,000. The federal amounts are those of the tests of l10n_ca_payroll.

K2P = 0.0505 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest Ontario rate.
"""

from datetime import date
from functools import partial
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_on_payroll.tools import health_premium
from odoo.addons.l10n_ca_payroll.tools import sources_page
from odoo.addons.l10n_ca_time_parameter.tools import bracket_constant


@tagged("post_install", "-at_install")
class TestOntarioPayroll(AccountTestInvoicingCommon):
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
        cls.ontario = cls.env.ref("base.state_ca_on")
        cls.alberta = cls.env.ref("base.state_ca_ab")
        cls.journal = cls.company_data["default_journal_misc"]
        # A rate basis under 200,000 gives the lowest EHT rate and the
        # exemption, without the warning of a basis left at 0.
        cls.account = cls.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": cls.company.id,
                "province_id": cls.ontario.id,
                "employer_tax_previous_payroll": 150000.0,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, province=None, start="2026-01-01", **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Ontario Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Ontario Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": start,
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": (province or self.ontario).id,
                "journal_id": self.journal.id,
                **vals,
            }
        )

    def _slip(
        self,
        contract,
        date_from,
        date_to,
        done=False,
        bonus=0.0,
        run=None,
        credit_note=False,
    ):
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
                "payslip_run_id": run.id if run else False,
                "credit_note": credit_note,
            }
        )
        slip.compute_sheet()
        if done:
            slip.action_payslip_done()
        return slip

    def _monthly_slips(self, contract, months, year=2026, done=True):
        return [
            self._slip(
                contract,
                date(year, month, 1),
                date(year, month, 28),
                done=done,
            )
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
    # Set-up and parameters
    # ------------------------------------------------------------------

    def test_setup_rules_and_accounts(self):
        codes = set(self.structure.rule_ids.mapped("code"))
        self.assertTrue(
            {"CA_ON_SAL", "CA_ON_WSIB_IE", "CA_ON_EHT", "CA_ON_WSIB"} <= codes
        )
        for xmlid in ("rule_on_eht", "rule_on_wsib"):
            rule = self.env.ref(f"l10n_ca_on_payroll.{xmlid}").with_company(
                self.company
            )
            self.assertEqual(rule.account_debit.code, "512121")
            self.assertEqual(rule.account_credit.code, "221206")
        # A second call adds nothing.
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)

    def test_ontario_constants(self):
        """KP derived from the shipped brackets equals the published table."""
        param = self.company._l10n_ca_param
        for day, expected in (
            (date(2026, 6, 1), [0, 2210, 4376, 5876, 8076]),
            (date(2025, 6, 1), [0, 2168, 4294, 5794, 7994]),
        ):
            brackets = param("l10n_ca.on.brackets", day)
            constants = [
                round(bracket_constant(amount, brackets))
                for amount in (40000, 100000, 120000, 200000, 300000)
            ]
            self.assertEqual(constants, expected, day)
        # 2026: 0.041 x 53,891 = 2,209.53 -> 2,210 and 2,209.53 + 0.0201 x
        # 107,785 = 4,376.01 -> 4,376.
        schedule = param("l10n_ca.on.health_premium", date(2026, 6, 1))
        self.assertEqual(health_premium(20000, schedule), 0.0)
        self.assertAlmostEqual(health_premium(25000, schedule), 300.0)
        self.assertAlmostEqual(health_premium(40000, schedule), 450.0)
        self.assertAlmostEqual(health_premium(50000, schedule), 600.0)
        self.assertAlmostEqual(health_premium(72400, schedule), 700.0)
        self.assertAlmostEqual(health_premium(150000, schedule), 750.0)
        self.assertAlmostEqual(health_premium(200400, schedule), 850.0)
        self.assertAlmostEqual(health_premium(500000, schedule), 900.0)

    # ------------------------------------------------------------------
    # Ontario income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # As in the federal test: C = 280.15, EI = 81.50, A = 12 x (5,000
        # - 280.15 x 0.01 / 0.0595) = 59,435.04, federal tax 444.86.
        # Ontario: A > 53,891 -> V 0.0915, KP 2,210
        #   K1P = 0.0505 x 12,989 = 655.94
        #   K2P = 0.0505 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.0505 x (2,796.79 + 978) = 190.63
        #   T4 = 0.0915 x 59,435.04 - 2,210 - 655.94 - 190.63 = 2,381.74
        #   V1 = 0 (T4 <= 5,818); S = 0 (2 x 300 < T4)
        #   V2 = min(600, 450 + 0.25 x (59,435.04 - 48,000)) = 600
        #   T2 = 2,381.74 + 600 = 2,981.73
        # T4127 rounds the tax of the period once: (5,338.29 + 2,981.74) /
        # 12 = 693.34, of which 444.86 federal and 248.48 Ontario.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -248.48,
                "NET": 5000.0 - 280.15 - 81.50 - 444.86 - 248.48,
                "CA_ON_SAL": 5000.0,
                "CA_ON_WSIB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("ON", tax_line.name)
        # The first pay of the year is inside the EHT exemption and the
        # company has no WSIB rate: no employer line.
        codes = slip.line_ids.mapped("code")
        self.assertNotIn("CA_ON_EHT", codes)
        self.assertNotIn("CA_ON_WSIB", codes)
        # The CRA collects the Ontario tax: box 22 = 444.86 + 248.48.
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 693.34)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Ontario, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        C = 0.0595 x (1,300 - 67.30) = 73.35, EI = 0.0163 x 1,300 = 21.19,
        F5A = 73.35 x 0.01 / 0.0595 = 12.33, A = 52 x (1,300 - 12.33 - 80)
        = 62,798.84. The CRA gives 5,957.85 of federal tax and 3,264.26 of
        Ontario tax for the year, (5,957.85 + 3,264.26) / 52 = 177.35 for
        the week, of which 5,957.85 / 52 = 114.57 federal.
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
                "CA_RRSP": -80.0,
                "CA_CPP": -73.35,
                "CA_EI": -21.19,
                "CA_FIT": -114.57,
                "CA_PIT": -62.78,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Ontario: 1,600 a week.

        The CPP and EI maximums are reached; the year-to-date pensionable
        earnings exceed the YMPE, so the pay bears 0.04 x 1,600 = 64 of
        CPP2, deducted from the income: A = 52 x 1,536 = 79,872, and K2
        takes both maximums. The CRA gives 9,406.39 federal and 4,957.90
        Ontario for the year: 14,364.29 / 52 = 276.24, of which 9,406.39 /
        52 = 180.89 federal.
        """
        # 6,933.33 x 12 / 52 = 1,600.00 a week.
        contract = self._contract(6933.33, schedule_pay="weekly")
        # A first pay of 76,000 reaches both maximums and bears (76,000 -
        # 74,600) x 0.04 = 56 of CPP2.
        first = self._slip(
            contract, "2026-01-05", "2026-01-11", done=True, bonus=74400.0
        )
        self._assert_lines(
            first, {"CA_CPP": -4230.45, "CA_EI": -1123.07, "CA_CPP2": -56.0}
        )
        slip = self._slip(contract, "2026-01-12", "2026-01-18")
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": -64.0,
                "CA_EI": 0.0,
                "CA_FIT": -180.89,
                "CA_PIT": -95.35,
            },
        )

    def test_tax_reduction_with_dependants(self):
        contract = self._contract(2800.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.0595 x (2,800 - 291.66) = 149.25; EI = 45.64
        # A = 12 x (2,800 - 149.25 / 5.95) = 33,298.99 -> V 0.0505, KP 0
        # K2P = 0.0505 x (12 x 149.25 x 0.0495 / 0.0595 + 12 x 45.64)
        #     = 0.0505 x (1,489.99 + 547.68) = 102.90
        # T4 = 0.0505 x 33,298.99 - 655.94 - 102.90 = 922.75
        # V2 = min(300, 0.06 x (33,298.99 - 20,000)) = 300
        # Without dependant: S = max(0, 2 x 300 - 922.75) = 0
        #   T2 = 922.75 + 300 = 1,222.75 -> 101.90
        self._assert_lines(slip, {"CA_PIT": -101.90})
        contract.l10n_ca_on_dependants_under_19 = 1
        slip.compute_sheet()
        # Y = 554: S = min(922.75, 2 x (300 + 554) - 922.75 = 785.25)
        # T2 = 922.75 + 300 - 785.25 = 437.50 -> 36.46
        self._assert_lines(slip, {"CA_PIT": -36.46})
        contract = self._contract(
            2500.0,
            l10n_ca_on_dependants_under_19=1,
            l10n_ca_on_disabled_dependants=1,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.0595 x (2,500 - 291.66) = 131.40; EI = 40.75
        # A = 12 x (2,500 - 131.40 / 5.95) = 29,734.99
        # K2P = 0.0505 x (1,311.80 + 489) = 90.94
        # T4 = 0.0505 x 29,734.99 - 655.94 - 90.94 = 754.73
        # Y = 2 x 554: S = min(754.73, 2 x 1,408 - 754.73) = 754.73, the
        # reduction cancels T4 but not the health premium:
        # T2 = V2 = min(300, 0.06 x 9,734.99) = 300 -> 25.00
        self._assert_lines(slip, {"CA_PIT": -25.0})

    def test_high_income_surtax(self):
        contract = self._contract(15000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.0595 x (15,000 - 291.66) = 875.15; EI = 244.50
        # A = 12 x (15,000 - 875.15 / 5.95) = 178,234.99 -> V 0.1216,
        #   KP 5,876
        # K2P = 0.0505 x (3,519.45 + 1,123.07), both maximums reached by
        #   P x amount (8,736.79 and 2,934) = 234.45
        # T4 = 0.1216 x 178,234.99 - 5,876 - 655.94 - 234.45 = 14,906.98
        # V1 = 0.20 x (14,906.98 - 5,818) + 0.36 x (14,906.98 - 7,446)
        #    = 1,817.80 + 2,685.95 = 4,503.75
        # V2 = min(750, 600 + 0.25 x 106,234.99) = 750; S = 0
        # T2 = 14,906.98 + 4,503.75 + 750 = 20,160.73 -> 1,680.06
        self._assert_lines(slip, {"CA_CPP": -875.15, "CA_PIT": -1680.06})

    def test_claim_exempt_health_premium_only(self):
        contract = self._contract(3000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.0595 x (3,000 - 291.66) = 161.15
        # A = 12 x (3,000 - 161.15 / 5.95) = 35,674.99 > 20,000
        # T2 = V2 = min(300, 0.06 x 15,674.99) = 300 -> 25.00
        self._assert_lines(slip, {"CA_CPP": -161.15, "CA_PIT": -25.0})
        contract = self._contract(1500.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 71.90, A = 12 x (1,500 - 71.90 / 5.95) = 17,854.99 <= 20,000
        self._assert_lines(slip, {"CA_PIT": 0.0})

    def test_claim_amount_credits_and_additional_tax(self):
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # As in test_monthly_5000 with K1P = 0 (claim code 0), K3P = 120:
        # T4 = 0.0915 x 59,435.04 - 2,210 - 190.63 - 120 = 2,917.68
        # T2 = 2,917.68 + 600 = 3,517.68 -> 293.14, plus 20.00 requested.
        self._assert_lines(slip, {"CA_PIT": -313.14})

    def test_union_dues_lower_the_ontario_tax(self):
        contract = self._contract(5000.0, l10n_ca_union_dues_amount=50.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # U1 = 50: A = 12 x (5,000 - 50 - 47.08) = 58,835.04; K2P as in
        # test_monthly_5000 (the dues do not change C nor EI).
        # T4 = 0.0915 x 58,835.04 - 2,210 - 655.94 - 190.63 = 2,326.84
        # T2 = 2,326.84 + 600 = 2,926.84 -> 243.90
        self._assert_lines(slip, {"CA_UNION": -50.0, "CA_PIT": -243.90})

    def test_bonus(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", bonus=3000.0)
        # Gross 8,000: C = 0.0595 x (8,000 - 291.66) = 458.65,
        #   EI = 130.40; F5 = 458.65 / 5.95 = 77.0840,
        #   F5A = F5 x 5,000 / 8,000 = 48.1775, F5B = 28.91
        # Regular A = 12 x (5,000 - 48.1775) = 59,421.87
        #   K2P of the regular contributions (280.15, 81.50) = 190.63
        #   T4 = 0.0915 x 59,421.87 - 2,210 - 655.94 - 190.63 = 2,380.53
        #   T2 = 2,380.53 + 600 = 2,980.53 -> 248.38
        # With the bonus: A = 59,421.87 + 3,000 - 28.91 = 62,392.96
        #   K2P adds the contributions on the bonus once:
        #   0.0505 x (2,796.79 + (458.65 - 280.15) x 0.0495 / 0.0595
        #   + 978 + (130.40 - 81.50)) = 0.0505 x 3,972.19 = 200.60
        #   T4 = 0.0915 x 62,392.96 - 2,210 - 655.94 - 200.60 = 2,642.42
        #   T2 = 2,642.42 + 600 = 3,242.42
        # TB = 3,242.42 - 2,980.53 = 261.89
        # Federal, same A: regular 444.63, TB 581.44 (l10n_ca_payroll).
        self._assert_lines(
            slip,
            {
                "GROSS": 8000.0,
                "CA_CPP": -458.65,
                "CA_EI": -130.40,
                "CA_F5B": 28.91,
                "CA_FIT": -(444.63 + 581.44),
                "CA_PIT": -(248.38 + 261.89),
            },
        )

    def test_bonus_flat_rate(self):
        """A with the bonus at most 5,000: the federal 15% covers Ontario."""
        contract = self._contract(200.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", bonus=1000.0)
        # A = 12 x 200 + 1,000 less the additional contributions < 5,000:
        # 15% of 1,000 on the federal line, no Ontario tax.
        self._assert_lines(slip, {"CA_FIT": -150.0, "CA_PIT": 0.0})

    def test_bonus_without_regular_pay(self):
        """T4127 bonus method: if I = 0, use the most recent I."""
        contract = self._contract(5000.0)
        self._monthly_slips(contract, (1, 2, 3))
        contract.wage = 0.0
        slip = self._slip(contract, "2026-04-01", "2026-04-30", bonus=10000.0)
        # As in the federal test: A without the bonus is the one of March,
        #   12 x (5,000 - 280.15 x 0.01 / 0.0595) = 59,435.04; C = 577.65,
        #   EI = 163.00, F5B = 97.08, A with = 59,435.04 + 9,902.92 =
        #   69,337.96. Both A in the 9.15% bracket (KP 2,210).
        # K2P with the bonus = 0.0505 x (577.65 x 0.0495 / 0.0595 + 163.00)
        #   = 0.0505 x 643.57 = 32.50; without = 0 (no regular contribution).
        # T4 with = 0.0915 x 69,337.96 - 2,210 - 655.94 - 32.50 = 3,445.98
        # T4 without = 0.0915 x 59,435.04 - 2,210 - 655.94 = 2,572.37
        # V1 = 0 and V2 = 600 for both, S = 0:
        # TB = 4,045.98 - 3,172.37 = 873.62 (0.0915 x 9,902.92 - 32.50).
        # Taking A without from this pay (0) would tax the whole bonus as
        # the only income of the year: 4,045.98.
        self._assert_lines(
            slip, {"GROSS": 10000.0, "CA_FIT": -1940.0, "CA_PIT": -873.62}
        )

    def test_2025_values(self):
        contract = self._contract(5000.0, start="2025-01-01")
        slip = self._slip(contract, "2025-03-01", "2025-03-31")
        # 2025: C = 280.15, EI = 0.0164 x 5,000 = 82.00, A = 59,435.04
        # A > 52,886 -> V 0.0915, KP 2,168; K1P = 0.0505 x 12,747 = 643.72
        # K2P = 0.0505 x (2,796.79 + 12 x 82) = 0.0505 x 3,780.79 = 190.93
        # T4 = 0.0915 x 59,435.04 - 2,168 - 643.72 - 190.93 = 2,435.66
        # T2 = 2,435.66 + 600 = 3,035.66 -> 252.97
        self._assert_lines(slip, {"CA_EI": -82.0, "CA_PIT": -252.97})
        contract = self._contract(15000.0, start="2025-01-01")
        slip = self._slip(contract, "2025-03-01", "2025-03-31")
        # A = 178,234.99 -> V 0.1216, KP 5,794
        # K2P = 0.0505 x (3,356.10 + 1,077.48) = 223.90 (2025 maximums)
        # T4 = 0.1216 x 178,234.99 - 5,794 - 643.72 - 223.90 = 15,011.76
        # V1 = 0.20 x (15,011.76 - 5,710) + 0.36 x (15,011.76 - 7,307)
        #    = 1,860.35 + 2,773.71 = 4,634.06; V2 = 750
        # T2 = 15,011.76 + 4,634.06 + 750 = 20,395.82 -> 1,699.65
        self._assert_lines(slip, {"CA_PIT": -1699.65})

    def test_2027_pay_warns_of_2026_amounts(self):
        """Without a 2027 version, a 2027 pay states the year it uses."""
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2027-03-01", "2027-03-31")
        self.assertIn(
            "The indexed amounts of 2027 are not entered (time parameter "
            "l10n_ca.on.bpa): this payslip uses those of 2026.",
            slip.l10n_ca_warning,
        )

    def _qpp_parameters(self):
        """Create the 2026 QPP rates as company parameters.

        They belong to the Quebec payroll module; company parameters win
        over shipped ones and never collide with them.
        """
        values = {
            "ympe": "74600",
            "yampe": "85000",
            "basic_exemption": "3500",
            "rate": "0.063",
            "base_rate": "0.053",
            "rate2": "0.04",
        }
        for key, value in values.items():
            self.env["base.time.parameter"].create(
                {
                    "name": f"QPP {key}",
                    "code": f"l10n_ca.qpp.{key}",
                    "type": "float",
                    "company_id": self.company.id,
                    "version_ids": [
                        (0, 0, {"date_from": "2026-01-01", "value": value})
                    ],
                }
            )

    def test_transfer_from_quebec_k2rp(self):
        """QPP withheld before a transfer to Ontario raises K2P (K2RP)."""
        self._qpp_parameters()
        contract = self._contract(10000.0, province=self.env.ref("base.state_ca_qc"))
        self._monthly_slips(contract, range(1, 7))
        contract.l10n_ca_province_id = self.ontario
        july, august, september = self._monthly_slips(contract, (7, 8, 9))
        # As in the federal test: DQ = 6 x 611.63 = 3,669.78 of QPP, CPP
        #   577.65 in July, 186.90 in August, 0 in September. EI: 6 x 130 in
        #   Quebec, 163 in July and August, 1,123.07 - 1,106 = 17.07 in
        #   September. Both maximums are reached in September.
        # K2RP: base credit maximum 3,519.45 + 3,669.78 x (0.053 - 0.0495)
        #   / 0.063 = 3,723.33; K2P = 0.0505 x (3,723.33 + 1,123.07) = 244.74
        # A = 12 x 10,000 = 120,000 (no F5A) -> V 0.1116, KP 4,376
        # T4 = 0.1116 x 120,000 - 4,376 - 655.94 - 244.74 = 8,115.31
        # V1 = 0.20 x 2,297.31 + 0.36 x 669.31 = 700.42; V2 = 750; S = 0
        # T2 = 8,115.31 + 700.42 + 750 = 9,565.73 -> 797.14
        # Without K2R, K2P = 234.45 and the tax would be 798.48.
        self._assert_lines(july, {"CA_CPP": -577.65})
        self._assert_lines(august, {"CA_CPP": -186.90})
        self._assert_lines(
            september, {"CA_CPP": 0.0, "CA_EI": -17.07, "CA_PIT": -797.14}
        )

    def test_other_province_not_computed(self):
        contract = self._contract(5000.0, province=self.alberta)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("NOT COMPUTED", line.name)
        codes = slip.line_ids.mapped("code")
        self.assertNotIn("CA_ON_SAL", codes)

    # ------------------------------------------------------------------
    # Employer Health Tax
    # ------------------------------------------------------------------

    def test_eht_rate_selection(self):
        day = date(2026, 6, 30)
        rate = partial(
            self.account._l10n_ca_employer_tax_rate, self.company, "l10n_ca.on"
        )
        self.assertEqual(rate(0.0, day), 0.0098)
        self.assertEqual(rate(200000, day), 0.0098)
        self.assertEqual(rate(200000.01, day), 0.01101)
        self.assertEqual(rate(300000, day), 0.01465)
        self.assertEqual(rate(400000, day), 0.01829)
        self.assertEqual(rate(400000.01, day), 0.0195)
        exemption = partial(
            self.account._l10n_ca_employer_tax_exemption, self.company, "l10n_ca.on"
        )
        self.assertEqual(exemption(5000000, day), 1000000)
        self.assertEqual(exemption(5000000.01, day), 0.0)
        self.account.employer_tax_charity = True
        self.assertEqual(exemption(9000000, day), 1000000)
        self.account.employer_tax_associated = True
        self.account.employer_tax_allocated_exemption = 1500000
        self.assertEqual(exemption(100000, day), 1000000)
        self.account.employer_tax_eligible = False
        self.assertEqual(exemption(100000, day), 0.0)

    def test_eht_across_the_exemption(self):
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 300000.0,
            }
        )
        contract = self._contract(5000.0)
        january, february, march, april = self._monthly_slips(contract, (1, 2, 3, 4))
        # Rate of 300,000 (more than 290,000 to 320,000): 1.465%.
        # January 5,000 and February 10,000 cumulative: under 12,000.
        self._assert_lines(january, {"CA_ON_EHT": 0.0, "CA_ON_SAL": 5000.0})
        self._assert_lines(february, {"CA_ON_EHT": 0.0})
        self.assertNotIn("CA_ON_EHT", january.line_ids.mapped("code"))
        # March: 15,000 - 12,000 = 3,000 taxable x 1.465% = 43.95
        # April: the whole 5,000 x 1.465% = 73.25
        self._assert_lines(march, {"CA_ON_EHT": 43.95})
        self._assert_lines(april, {"CA_ON_EHT": 73.25})
        line = march.line_ids.filtered(lambda line: line.code == "CA_ON_EHT")
        self.assertRegex(line.name, r"1[.,]465")

    def _march_batch(self):
        return self.env["hr.payslip.run"].create(
            {
                "name": "March 2026",
                "date_start": "2026-03-01",
                "date_end": "2026-03-31",
                "company_id": self.company.id,
            }
        )

    def test_eht_batch_confirm_order(self):
        """Each pair of payslips of a batch shares the exemption once."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 5000.0,
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 300000.0,
            }
        )
        run = self._march_batch()
        first = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-31", run=run)
        second = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-31", run=run)
        self.assertLess(first.id, second.id)
        # The first payslip takes the whole exemption of 5,000; the second
        # counts it (R = 5,000) and bears 5,000 x 1.465% = 73.25.
        self._assert_lines(first, {"CA_ON_EHT": 0.0})
        self._assert_lines(second, {"CA_ON_EHT": 73.25})
        # Confirmed latest first, as the list of the batch shows them, each
        # payslip is recomputed: the second still counts the first, and the
        # first does not count the second, done but later in its batch.
        second.action_payslip_done()
        first.action_payslip_done()
        self._assert_lines(first, {"CA_ON_EHT": 0.0})
        self._assert_lines(second, {"CA_ON_EHT": 73.25})

    def test_eht_batch_pay_date_order(self):
        """In a batch, a payslip paid earlier counts first, whatever its id."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 5000.0,
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 300000.0,
            }
        )
        run = self._march_batch()
        late = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-31", run=run)
        early = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-15", run=run)
        self.assertLess(late.id, early.id)
        late.compute_sheet()
        # The payslip paid on March 15 takes the whole exemption of 5,000;
        # the one paid on March 31 counts it (R = 5,000) and bears 5,000 x
        # 1.465% = 73.25, in either confirmation order.
        for slip in (late, early, None):
            self._assert_lines(early, {"CA_ON_EHT": 0.0})
            self._assert_lines(late, {"CA_ON_EHT": 73.25})
            if slip:
                slip.action_payslip_done()

    def test_eht_credit_note(self):
        """A credit-note payslip reverses the EHT of the pay it takes back."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 300000.0,
            }
        )
        contract = self._contract(5000.0)
        self._monthly_slips(contract, (1, 2, 3))
        refund = self._slip(
            contract, "2026-03-01", "2026-03-28", done=True, credit_note=True
        )
        # R = 15,000; the credit note takes G = 5,000 out of it:
        # EHT = 1.465% x (max(0, 15,000 - 12,000) - max(0, 10,000 - 12,000))
        #     = 1.465% x 3,000 = 43.95, the EHT of March, counted negatively.
        # Taken as a pay added to R it would be 5,000 x 1.465% = 73.25.
        self._assert_lines(refund, {"CA_ON_SAL": 5000.0, "CA_ON_EHT": 43.95})
        # R = 10,000: April uses the 2,000 of exemption left and bears
        # 3,000 x 1.465% = 43.95.
        april = self._slip(contract, "2026-04-01", "2026-04-28")
        self._assert_lines(april, {"CA_ON_EHT": 43.95})

    def test_eht_basis_not_entered(self):
        """A rate basis left at 0 is applied with a warning."""
        self.account.employer_tax_previous_payroll = 0.0
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        warning = (
            f"The total remuneration of {self.company.name} in Ontario that sets "
            "the employer payroll tax is 0"
        )
        self.assertIn(warning, slip.l10n_ca_warning)
        self.account.write(
            {
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 0.0,
            }
        )
        slip.compute_sheet()
        self.assertIn(warning, slip.l10n_ca_warning)
        self.account.employer_tax_estimated_payroll = 300000.0
        slip.compute_sheet()
        self.assertFalse(slip.l10n_ca_warning)

    def test_eht_refund_and_negative_earnings(self):
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 300000.0,
            }
        )
        contract = self._contract(5000.0)
        march = self._monthly_slips(contract, (1, 2, 3))[-1]
        april = self._slip(contract, "2026-04-01", "2026-04-28")
        # R = 15,000: April bears 5,000 x 1.465% = 73.25.
        self._assert_lines(april, {"CA_ON_EHT": 73.25})
        # A recovery entered as negative earnings keeps its sign:
        # -2,000 -> taxable max(0, 13,000 - 12,000) - (15,000 - 12,000) =
        # -2,000 -> -29.30; -4,000 only reverses the 3,000 above the
        # exemption -> -43.95.
        vals = april._l10n_ca_compute(contract, -2000.0)
        self.assertAlmostEqual(vals["province_remuneration"], -2000.0)
        self.assertAlmostEqual(vals["employer_tax"], -29.30)
        vals = april._l10n_ca_compute(contract, -4000.0)
        self.assertAlmostEqual(vals["employer_tax"], -43.95)
        self.assertAlmostEqual(vals["wcb_insurable"], 0.0)
        # The refund of March counts negatively: R = 10,000 and April
        # bears max(0, 15,000 - 12,000) x 1.465% = 43.95.
        march.refund_sheet()
        april.compute_sheet()
        self._assert_lines(april, {"CA_ON_EHT": 43.95})

    def test_eht_without_exemption(self):
        self.account.employer_tax_previous_payroll = 6000000.0
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # 6,000,000 > 5,000,000: no exemption, rate 1.95% x 5,000 = 97.50
        self._assert_lines(slip, {"CA_ON_EHT": 97.50})
        self.account.write(
            {
                "employer_tax_previous_payroll": 150000.0,
                "employer_tax_eligible": False,
            }
        )
        slip.compute_sheet()
        # Not an eligible employer: 0.98% x 5,000 = 49.00 from the first pay.
        self._assert_lines(slip, {"CA_ON_EHT": 49.0})

    # ------------------------------------------------------------------
    # WSIB
    # ------------------------------------------------------------------

    def test_wsib_up_to_the_maximum(self):
        self.account.wcb_rate = 1.30
        contract = self._contract(50000.0)
        slips = self._monthly_slips(contract, (1, 2, 3, 4))
        # 2026 maximum 121,700: 50,000, 50,000, then 121,700 - 100,000 =
        # 21,700, then 0. Premium = 1.30 x insurable / 100.
        self.assertEqual(
            [self._line(s, "CA_ON_WSIB_IE") for s in slips],
            [50000.0, 50000.0, 21700.0, 0.0],
        )
        self.assertEqual(
            [self._line(s, "CA_ON_WSIB") for s in slips],
            [650.0, 650.0, 282.10, 0.0],
        )
        exempt = self._contract(5000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self.assertNotIn("CA_ON_WSIB", slip.line_ids.mapped("code"))
        self._assert_lines(slip, {"CA_ON_WSIB_IE": 0.0})

    def test_wsib_batch_peers(self):
        """Two payslips of one employee in a batch share the maximum."""
        self.account.wcb_rate = 1.30
        contract = self._contract(50000.0)
        self._monthly_slips(contract, (1, 2))
        run = self._march_batch()
        first, second = (
            self._slip(contract, "2026-03-01", "2026-03-31", run=run) for _i in (1, 2)
        )
        # 100,000 so far: the first takes 121,700 - 100,000 = 21,700, the
        # second counts it and has no room left, in either confirmation
        # order.
        for slip in (second, first, None):
            self._assert_lines(first, {"CA_ON_WSIB_IE": 21700.0, "CA_ON_WSIB": 282.10})
            self._assert_lines(second, {"CA_ON_WSIB_IE": 0.0})
            if slip:
                slip.action_payslip_done()

    def test_wsib_credit_note(self):
        """A credit note reverses the insurable earnings the pay counted."""
        self.account.wcb_rate = 1.30
        contract = self._contract(50000.0)
        self._monthly_slips(contract, (1, 2, 3))
        refund = self._slip(
            contract, "2026-03-01", "2026-03-28", done=True, credit_note=True
        )
        # IE so far 121,700 (50,000, 50,000, 21,700), S = 150,000. The
        # remuneration left, S - G = 100,000, is insurable in full:
        # IE = min(50,000, 121,700 - min(121,700, 100,000)) = 21,700, the
        # IE of March -> 1.30 x 21,700 / 100 = 282.10, counted negatively.
        self._assert_lines(refund, {"CA_ON_WSIB_IE": 21700.0, "CA_ON_WSIB": 282.10})
        # IE so far 100,000: April takes 21,700 again.
        april = self._slip(contract, "2026-04-01", "2026-04-28")
        self._assert_lines(april, {"CA_ON_WSIB_IE": 21700.0})

    def test_wsib_2025_maximum(self):
        self.account.wcb_rate = 1.30
        contract = self._contract(100000.0, start="2025-01-01")
        january, february = self._monthly_slips(contract, (1, 2), year=2025)
        # 2025 maximum 117,000: 100,000 then 17,000 -> 1,300.00 and 221.00
        self._assert_lines(january, {"CA_ON_WSIB": 1300.0})
        self._assert_lines(february, {"CA_ON_WSIB_IE": 17000.0, "CA_ON_WSIB": 221.0})

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    @freeze_time("2026-11-15")
    def test_watchers_of_the_ontario_pages(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        rows = "".join(
            f"<tr><td>{label}</td><td>{rate}</td></tr>"
            for label, rate in (
                ("Up to $200,000.00", "0.98%"),
                ("$200,000.01 to $230,000.00", "1.101%"),
                ("$230,000.01 to $260,000.00", "1.223%"),
                ("$260,000.01 to $290,000.00", "1.344%"),
                ("$290,000.01 to $320,000.00", "1.465%"),
                ("$320,000.01 to $350,000.00", "1.586%"),
                ("$350,000.01 to $380,000.00", "1.708%"),
                ("$380,000.01 to $400,000.00", "1.829%"),
                ("Over $400,000.00", "1.95%"),
            )
        )
        eht = (
            "<table><tr><th>Total Ontario remuneration</th><th>Rate</th></tr>"
            f"{rows}</table><p>The exemption amount is currently $ 1 million.</p>"
        )

        def fetch(self_, url, probe=False):
            if "employer-health-tax" in url:
                return 200, f"<html><body>{eht}</body></html>".encode()
            year = int(url.rsplit("/", 1)[1][:4])
            if year > 2027:
                return 404, b""
            previous = {2026: "117,000", 2027: "121,700"}[year]
            value = {2026: "121,700", 2027: "126,700"}[year]
            text = (
                f"The maximum insurable earnings ceiling for {year} is ${value}, "
                f"compared to ${previous} in {year - 1}."
            )
            return 200, f"<html><body><p>{text}</p></body></html>".encode()

        eht_source = self.env.ref("l10n_ca_on_payroll.source_eht_guide")
        wsib = self.env.ref("l10n_ca_on_payroll.source_wsib_2027_rates")
        with patch.object(Source, "_l10n_ca_fetch", fetch):
            (eht_source | wsib).with_context(lang="en_US").action_l10n_ca_watch()
        # The EHT page gives the rates and the exemption shipped for 2026 and
        # 2027; the WSIB maximums 121,700 and 126,700 are shipped too.
        self.assertEqual(eht_source.watch_state, "ok", eht_source.watch_message)
        self.assertEqual(wsib.watch_state, "ok", wsib.watch_message)
        # In 2027, the 2028 page does not exist yet: not a page change.
        with freeze_time("2027-03-01"), patch.object(Source, "_l10n_ca_fetch", fetch):
            wsib.with_context(lang="en_US").action_l10n_ca_watch()
        self.assertEqual(wsib.watch_state, "pending")
        self.assertIn("2028: not yet published.", wsib.watch_message)

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.on.%")]
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
