# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Quebec payslips checked against TP-1015.F-V (2026-01) and T4127.

Shipped 2026 parameters used by the derivations: QPP MPE 74,600,
additional MPE 85,000, exemption 3,500, rate 6.30% (base 5.30%), QPP2 4%
(maximums 4,479.30 and 416); EI Quebec 1.30% up to 68,900 (maximum
895.70); QPIP 0.430% / 0.602% up to 103,000 (maximums 442.90 / 620.06);
Quebec brackets 14% / 19% from 54,345 (K 2,717) / 24% from 108,680
(K 8,151) / 25.75% from 132,245 (K 10,465); basic personal amount 18,952,
credit rate 14%; deduction for workers 6% up to 1,450; HSF 1.65% up to a
total payroll of 1,000,000; CNT 0.06% up to 103,000. Federal: brackets
14% / 20.5% from 58,523 (K 3,804) / 26% from 117,045 (K 10,241), BPA
16,452, CEA 1,501, abatement 16.5%.
"""

from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_qc_payroll.tools import quebec_constant


@tagged("post_install", "-at_install")
class TestQuebecPayroll(AccountTestInvoicingCommon):
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
        cls.quebec = cls.env.ref("base.state_ca_qc")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(
        self, wage, province=None, schedule="monthly", birthday="1985-06-15", **vals
    ):
        employee = self.env["hr.employee"].create(
            {
                "name": "Quebec Test Employee",
                "birthday": birthday,
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Quebec Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": schedule,
                "l10n_ca_province_id": (province or self.quebec).id,
                "journal_id": self.journal.id,
                **vals,
            }
        )

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

    def _monthly_slips(self, contract, months, done=True):
        return [
            self._slip(
                contract,
                date(2026, month, 1),
                date(2026, month, 28 if month == 2 else 30),
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
            {"CA_QC_SAL", "CA_QPIP", "CA_QPIP_ER", "CA_QC_HSF", "CA_QC_CNT"} <= codes
        )
        rule = self.env.ref("l10n_ca_qc_payroll.rule_hsf").with_company(self.company)
        self.assertEqual(rule.account_debit.code, "512121")
        self.assertEqual(rule.account_credit.code, "221206")
        qpip = self.env.ref("l10n_ca_qc_payroll.rule_qpip").with_company(self.company)
        self.assertEqual(qpip.account_credit.code, "221203")
        # A second call adds nothing.
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)

    def test_quebec_bracket_constants(self):
        """K derived from the shipped brackets equals the published table."""
        brackets = self.company._l10n_ca_param("l10n_ca.qc.brackets", date(2026, 6, 1))
        self.assertEqual(quebec_constant(50000, brackets), 0)
        self.assertEqual(quebec_constant(60000, brackets), 2717)
        self.assertEqual(quebec_constant(120000, brackets), 8151)
        self.assertEqual(quebec_constant(200000, brackets), 10465)
        brackets_2025 = self.company._l10n_ca_param(
            "l10n_ca.qc.brackets", date(2025, 6, 1)
        )
        # 2025 table: 2,662, 7,987 and 10,255.
        self.assertEqual(quebec_constant(60000, brackets_2025), 2662)
        self.assertEqual(quebec_constant(120000, brackets_2025), 7987)
        self.assertEqual(quebec_constant(200000, brackets_2025), 10255)

    def test_hsf_rate_selection(self):
        day = date(2026, 6, 30)
        rate = self.company._l10n_ca_qc_hsf_rate
        # Up to 1,000,000: S = 1 -> 1.2662 + 0.3838 = 1.65
        self.assertEqual(rate(0.0, day), 1.65)
        self.assertEqual(rate(1000000, day), 1.65)
        # 2,000,000: 1.2662 + 0.3838 * 2 = 2.0338 -> 2.03
        self.assertEqual(rate(2000000, day), 2.03)
        # From 7,800,000: 1.2662 + 0.3838 * 7.8 = 4.25984 -> 4.26
        self.assertEqual(rate(7800000, day), 4.26)
        self.assertEqual(rate(20000000, day), 4.26)
        self.company.l10n_ca_qc_hsf_sector = "primary_manufacturing"
        # 0.8074 + 0.4426 * 2 = 1.6926 -> 1.69, the example of TP-1015.G.
        self.assertEqual(rate(2000000, day), 1.69)
        self.assertEqual(rate(500000, day), 1.25)
        self.company.l10n_ca_qc_hsf_sector = "public"
        self.assertEqual(rate(500000, day), 4.26)

    # ------------------------------------------------------------------
    # Payslips
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # QPP C = 0.063 * (5,000 - 3,500 / 12 = 291.66) = 296.63; C2 = 0
        # EI = 0.013 * 5,000 = 65.00, employer 1.4 * 65 = 91.00
        # QPIP = 0.0043 * 5,000 = 21.50, employer 0.00602 * 5,000 = 30.10
        # Federal: A = 12 * (5,000 - 296.63 * 0.01 / 0.063) = 59,434.99,
        #   K2 = 0.14 * (12 * 296.63 * 0.053 / 0.063) + 0.14 * 780
        #      + 0.14 * min(12 * 21.50, 442.90) = 564.56
        #   T3 = 0.205 * 59,434.99 - 3,804 - 2,303.28 - 564.56 - 210.14
        #      = 5,302.20; T1 = 0.835 * T3 = 4,427.33 -> 368.94
        # Quebec: H = min(0.06 * 5,000, 1,450 / 12) = 120.83
        #   CSA = 296.63 * 0.01 / 0.063 = 47.08
        #   I = 12 * (5,000 - 120.83 - 47.08) = 57,985.08 -> T 0.19, K 2,717
        #   Y = 0.19 * 57,985.08 - 2,717 - 0.14 * 18,952 = 5,646.89
        #   A = 5,646.89 / 12 = 470.57
        # HSF 1.65% * 5,000 = 82.50; CNT 0.06% * 5,000 = 3.00
        self._assert_lines(
            slip,
            {
                "CA_CPP": -296.63,
                "CA_CPP2": 0.0,
                "CA_EI": -65.0,
                "CA_QPIP": -21.50,
                "CA_FIT": -368.94,
                "CA_PIT": -470.57,
                "NET": 5000.0 - 296.63 - 65.0 - 21.50 - 368.94 - 470.57,
                "CA_CPP_ER": 296.63,
                "CA_EI_ER": 91.0,
                "CA_QPIP_ER": 30.10,
                "CA_QC_SAL": 5000.0,
                "CA_QC_HSF": 82.50,
                "CA_QC_CNT": 3.00,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("QC", tax_line.name)
        # No CNESST rate and a payroll under the WSDRF threshold: no line.
        self.assertFalse(
            slip.line_ids.filtered(
                lambda line: line.code in ("CA_QC_CNESST", "CA_QC_WSDRF")
            )
        )

    def test_biweekly_3000(self):
        # Monthly wage 6,500 -> 6,500 * 12 / 26 = 3,000 per pay.
        contract = self._contract(6500.0, schedule="bi-weekly")
        slip = self._slip(contract, "2026-03-02", "2026-03-15")
        # QPP: exemption 3,500 / 26 = 134.61 (truncated)
        #   C = 0.063 * (3,000 - 134.61) = 180.52
        # EI = 0.013 * 3,000 = 39.00; QPIP 12.90, employer 18.06
        # Federal: A = 26 * (3,000 - 180.52 / 6.3) = 77,254.99
        #   K2 = 0.14 * (26 * 180.52 * 0.053 / 0.063) + 0.14 * 895.70
        #        (26 * 39 = 1,014 capped) + 0.14 * 26 * 12.90 = 699.92
        #   T3 = 0.205 * 77,254.99 - 3,804 - 2,303.28 - 699.92 - 210.14
        #      = 8,819.94; T1 = 7,364.65 -> 283.26
        # Quebec: H = min(180, 1,450 / 26 = 55.769) = 55.77
        #   CSA = 180.52 / 6.3 = 28.65
        #   I = 26 * (3,000 - 55.77 - 28.65) = 75,805.08
        #   Y = 0.19 * 75,805.08 - 2,717 - 2,653.28 = 9,032.69 -> 347.41
        self._assert_lines(
            slip,
            {
                "BASIC": 3000.0,
                "CA_CPP": -180.52,
                "CA_EI": -39.0,
                "CA_QPIP": -12.90,
                "CA_QPIP_ER": 18.06,
                "CA_FIT": -283.26,
                "CA_PIT": -347.41,
                "CA_QC_HSF": 49.50,
                "CA_QC_CNT": 1.80,
            },
        )

    def test_claim_additional_tax_and_exemption(self):
        contract = self._contract(
            5000.0,
            l10n_ca_qc_claim_type="custom",
            l10n_ca_qc_claim_amount=0.0,
            l10n_ca_qc_additional_tax=25.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # E = 0: Y = 0.19 * 57,985.08 - 2,717 = 8,300.17 -> 691.68 + 25.00
        self._assert_lines(slip, {"CA_PIT": -716.68})
        contract.l10n_ca_qc_tax_exempt = True
        slip = self._slip(contract, "2026-04-01", "2026-04-30")
        self._assert_lines(slip, {"CA_PIT": 0.0, "CA_FIT": -368.94})

    def test_claim_indexation(self):
        """Line 7 of an earlier TP-1015.3 is indexed (TP-1015.F, E1)."""
        contract = self._contract(
            5000.0,
            l10n_ca_qc_claim_type="custom",
            l10n_ca_qc_claim_amount=20000.0,
            l10n_ca_qc_claim_year=2026,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # Form of 2026: E = 20,000;
        #   Y = 0.19 * 57,985.08 - 2,717 - 0.14 * 20,000 = 5,500.17 -> 458.35
        self._assert_lines(slip, {"CA_PIT": -458.35})
        contract.l10n_ca_qc_claim_year = 2025
        slip = self._slip(contract, "2026-04-01", "2026-04-30")
        # Form of 2025: E1 = 20,000 * 1.0205 = 20,410;
        #   Y = 11,017.17 - 2,717 - 2,857.40 = 5,442.77 -> 453.56
        self._assert_lines(slip, {"CA_PIT": -453.56})
        # No indexation rate of 2025 is shipped: a form of 2024 cannot be
        # indexed to 2026.
        contract.l10n_ca_qc_claim_year = 2024
        with self.assertRaises(UserError):
            self._slip(contract, "2026-05-01", "2026-05-31")

    def test_example_appendix_1(self):
        """TP-1015.F appendix 1: RPP (F) and labour-sponsored funds (Q, Q1)."""
        # 8,666.67 * 12 / 26 = 4,000.00 every two weeks.
        contract = self._contract(
            8666.67,
            schedule="bi-weekly",
            l10n_ca_rpp_amount=200.0,
            l10n_ca_qc_claim_type="custom",
            l10n_ca_qc_claim_amount=21830.0,
            l10n_ca_qc_claim_year=2026,
            l10n_ca_qc_ftq_withholding=100.0,
            l10n_ca_qc_fondaction_withholding=150.0,
        )
        slip = self._slip(contract, "2026-03-02", "2026-03-15")
        # C = 0.063 * (4,000 - 134.61) = 243.52, CSA = 38.65, H = 55.77
        # I = 26 * (4,000 - 200 - 55.77 - 38.65) = 96,345.08
        # Y = 0.19 * 96,345.08 - 2,717 - 0.14 * 21,830 - 0.15 * 26 * 100
        #   - 0.15 * 26 * 150 = 11,557.37 -> 444.51, as in the appendix.
        self._assert_lines(
            slip,
            {"BASIC": 4000.0, "CA_RPP": -200.0, "CA_CPP": -243.52, "CA_PIT": -444.51},
        )
        rl1 = slip._l10n_ca_qc_rl1_values(2026)
        self.assertAlmostEqual(rl1["box_a"], 4000.0)
        self.assertAlmostEqual(rl1["box_d"], 200.0)

    def test_quebec_only_deduction(self):
        """A rule of category CA_QC_TAXDED lowers the Quebec tax only."""
        rule = self.env["hr.salary.rule"].create(
            {
                "name": "FHSA Contribution",
                "code": "TEST_FHSA",
                "sequence": 50,
                "category_id": self.env.ref(
                    "l10n_ca_qc_payroll.categ_qc_tax_deduction"
                ).id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": -100.0,
            }
        )
        self.structure.rule_ids = [(4, rule.id)]
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # Federal tax as in test_monthly_5000: 368.94.
        # Quebec: I = 12 * (5,000 - 100 - 120.83 - 47.08) = 56,785.08
        #   Y = 0.19 * 56,785.08 - 2,717 - 0.14 * 18,952 = 5,418.89 -> 451.57
        self._assert_lines(
            slip, {"TEST_FHSA": -100.0, "CA_FIT": -368.94, "CA_PIT": -451.57}
        )

    def test_example_appendix_2(self):
        """TP-1015.F appendix 2: tax on a retroactive payment, second method.

        1,500 a week with an RPP contribution of 100; a retroactive payment
        of 4,000 of which 400 go to the RPP.
        """
        Rule = self.env["hr.salary.rule"]
        regular_rpp = Rule.create(
            {
                "name": "Registered Pension Plan",
                "code": "TEST_RPP",
                "sequence": 50,
                "category_id": self.env.ref(
                    "l10n_ca_qc_payroll.categ_qc_tax_deduction"
                ).id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": -100.0,
            }
        )
        lump_rpp = Rule.create(
            {
                "name": "Registered Pension Plan on the Retroactive Payment",
                "code": "TEST_RPP_LUMP",
                "sequence": 51,
                "category_id": self.env.ref("l10n_ca_payroll.categ_lump_ded").id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": -400.0,
            }
        )
        self.structure.rule_ids = [(4, regular_rpp.id), (4, lump_rpp.id)]
        # 6,500 * 12 / 52 = 1,500.00 a week.
        contract = self._contract(6500.0, schedule="weekly")
        slip = self._slip(contract, "2026-05-11", "2026-05-17", bonus=4000.0)
        # C = 0.063 * (5,500 - 67.30) = 342.26, CS = 342.26 / 6.3 = 54.327
        # CSA = 54.327 * 1,500 / 5,500 = 14.82, CSB = 54.327 * 4,000 /
        # 5,500 = 39.51; H = min(90, 1,450 / 52) = 27.88
        # Regular pay: I = 52 * (1,500 - 100 - 27.88 - 14.82) = 70,579.60
        #   Y = 0.19 * 70,579.60 - 2,717 - 0.14 * 18,952 = 8,039.84
        #   -> 154.61
        # Payment: I = 70,579.60 + 3,600 - 39.51 = 74,140.09 -> T = 19%
        #   A = 0.19 * (3,600 - 39.51) = 676.49, as in the appendix.
        self._assert_lines(
            slip,
            {
                "GROSS": 5500.0,
                "TEST_RPP": -100.0,
                "TEST_RPP_LUMP": -400.0,
                "CA_CPP": -342.26,
                "CA_NPP": 3600.0,
                "CA_F5B": 39.51,
                "CA_PIT": -(154.61 + 676.49),
            },
        )

    def test_lump_sum_flat_rate(self):
        """Salary and lump sums of at most the basic personal amount: 7%."""
        contract = self._contract(1000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", bonus=2000.0)
        # 12 * 1,000 + 2,000 = 14,000 <= 18,952: 7% of 2,000; the regular
        # pay of 1,000 bears no Quebec tax.
        self._assert_lines(slip, {"GROSS": 3000.0, "CA_PIT": -140.0})
        slip.action_payslip_done()
        slip = self._slip(contract, "2026-04-01", "2026-04-30", bonus=5000.0)
        # 12,000 + 2,000 + 5,000 = 19,000 > 18,952: second method.
        # March: C = 0.063 * (3,000 - 291.66) = 170.63, CS = 27.0841,
        #   CSB1 = 27.0841 * 2,000 / 3,000 = 18.06
        # April: C = 0.063 * (6,000 - 291.66) = 359.63, CS = 57.0841,
        #   CSA = 9.51, CSB = 47.57, H = min(60, 120.83) = 60
        #   I = 12 * (1,000 - 60 - 9.51) + 2,000 + 5,000 - 18.06 - 47.57
        #     = 18,100.25 -> T = 14%; A = 0.14 * (5,000 - 47.57) = 693.34
        self._assert_lines(slip, {"CA_F5B": 47.57, "CA_PIT": -693.34})

    def test_bonus_counts_in_rl1_box_a(self):
        """A bonus is employment income, pensionable and insurable."""
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", done=True, bonus=1000.0)
        # QPP C = 0.063 * (6,000 - 291.66) = 359.63; QPIP 0.0043 * 6,000
        self._assert_lines(
            slip,
            {
                "GROSS": 6000.0,
                "CA_CPP": -359.63,
                "CA_QPIP": -25.80,
                "CA_QC_SAL": 6000.0,
            },
        )
        values = slip._l10n_ca_qc_rl1_values(2026)
        self.assertAlmostEqual(values["box_a"], 6000.0, places=2)
        self.assertAlmostEqual(values["box_g"], 6000.0, places=2)
        self.assertAlmostEqual(values["box_i"], 6000.0, places=2)

    def test_amounts_from_a_later_date(self):
        """J1 and K1 set after the first pay are spread over the pays left."""
        contract = self._contract(
            5000.0,
            l10n_ca_qc_authorized_deductions=6000.0,
            l10n_ca_qc_authorized_credits=600.0,
            l10n_ca_qc_authorized_date="2026-07-01",
        )
        first_half = self._monthly_slips(contract, range(1, 7))
        # Pays before July 1: no J1 nor K1, as in test_monthly_5000.
        self._assert_lines(first_half[0], {"CA_PIT": -470.57})
        slip = self._slip(contract, "2026-07-01", "2026-07-31")
        # PR = 12 - 6 = 6: J1 = 12 * 6,000 / 6 = 12,000, K1 = 1,200
        # I = 57,985.08 - 12,000 = 45,985.08 -> T 0.14, K 0
        # Y = 6,437.91 - 1,200 - 2,653.28 = 2,584.63 -> 215.39
        self._assert_lines(slip, {"CA_PIT": -215.39})

    def test_minimum_contribution_of_one_cent(self):
        """QPP and employee QPIP above 0 but below 0.005 are 0.01."""
        contract = self._contract(291.70)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.063 * (291.70 - 291.66) = 0.00252
        self._assert_lines(slip, {"CA_CPP": -0.01, "CA_CPP_ER": 0.01})
        contract = self._contract(0.50)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # QPIP 0.0043 * 0.50 = 0.00215 -> 0.01; employer 0.00301 -> 0.00
        self._assert_lines(slip, {"CA_QPIP": -0.01, "CA_QPIP_ER": 0.0})

    def test_low_income_no_quebec_tax(self):
        contract = self._contract(1500.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.063 * (1,500 - 291.66) = 76.13; H = min(90, 120.83) = 90
        # CSA = 76.13 / 6.3 = 12.08; I = 12 * (1,500 - 90 - 12.08)
        #   = 16,775.04: 0.14 * I = 2,348.51 < 0.14 * 18,952 -> Y = 0
        self._assert_lines(slip, {"CA_CPP": -76.13, "CA_PIT": 0.0})

    def test_employer_rates_cnesst_wsdrf(self):
        self.company.write(
            {
                "l10n_ca_qc_total_payroll_estimate": 2500000.0,
                "l10n_ca_qc_wsdrf_payroll_estimate": 1500000.0,
                "l10n_ca_qc_cnesst_rate": 1.25,
            }
        )
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # HSF: 1.2662 + 0.3838 * 2.5 = 2.2257 -> 2.23% * 5,000 = 111.50
        # CNESST 1.25 / 100 * 5,000 = 62.50. The group payroll exceeds
        # 2,000,000 but the payroll of the company does not: no WSDRF.
        self._assert_lines(slip, {"CA_QC_HSF": 111.50, "CA_QC_CNESST": 62.50})
        self.assertNotIn("CA_QC_WSDRF", slip.line_ids.mapped("code"))
        self.company.l10n_ca_qc_wsdrf_payroll_estimate = 2100000.0
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # WSDRF 1% * 5,000 = 50.00
        self._assert_lines(slip, {"CA_QC_HSF": 111.50, "CA_QC_WSDRF": 50.0})
        contract.l10n_ca_qc_cnesst_exempt = True
        self.company.l10n_ca_qc_cnt_exempt = True
        slip = self._slip(contract, "2026-04-01", "2026-04-30")
        codes = slip.line_ids.mapped("code")
        self.assertNotIn("CA_QC_CNESST", codes)
        self.assertNotIn("CA_QC_CNT", codes)

    def test_hsf_year_to_date_basis(self):
        self.company.l10n_ca_qc_hsf_basis = "year_to_date"
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-01-01", "2026-01-31")
        # Payroll to date 5,000 <= 1,000,000 -> 1.65%
        self._assert_lines(slip, {"CA_QC_HSF": 82.50})
        # The payroll of the associated employers counts:
        # 1.2662 + 0.3838 * 2.005 = 2.0357 -> 2.04% * 5,000 = 102.00
        self.company.l10n_ca_qc_associated_payroll = 2000000.0
        slip = self._slip(contract, "2026-02-01", "2026-02-28")
        self._assert_lines(slip, {"CA_QC_HSF": 102.0})

    def test_hsf_year_to_date_remittance_period(self):
        """The new employer rate is the one of the end of the period."""
        self.company.write(
            {
                "l10n_ca_qc_hsf_basis": "year_to_date",
                "l10n_ca_qc_hsf_sector": "primary_manufacturing",
                "l10n_ca_qc_remitter_type": "monthly",
            }
        )
        second = self._slip(
            self._contract(525000.0), "2026-03-16", "2026-03-31", done=True
        )
        # Payroll to date 525,000 -> 1.25%
        self._assert_lines(second, {"CA_QC_HSF": 6562.50})
        first = self._slip(
            self._contract(525000.0), "2026-03-01", "2026-03-15", done=True
        )
        # Paid by the end of March: 1,050,000
        #   -> 0.8074 + 0.4426 * 1.05 = 1.2721 -> 1.27%
        self._assert_lines(first, {"CA_QC_HSF": 6667.50})
        remittances = self.env["l10n_ca.qc.payroll.remittance"]._l10n_ca_qc_generate(
            self.company, 2026
        )
        # The March payment applies 1.27% to the whole March payroll.
        self.assertEqual(len(remittances), 1)
        self.assertAlmostEqual(remittances.hsf, 13335.0)

    def test_ontario_has_no_quebec_lines(self):
        contract = self._contract(5000.0, province=self.ontario)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        codes = set(slip.line_ids.mapped("code"))
        self.assertFalse(codes & {"CA_QPIP", "CA_QPIP_ER", "CA_QC_HSF", "CA_QC_SAL"})
        self.assertEqual(slip.l10n_ca_pension_plan, "cpp")

    # ------------------------------------------------------------------
    # QPP age limits
    # ------------------------------------------------------------------

    def test_qpp_until_the_year_of_72(self):
        # Turns 72 in 2026: contributions all year, no stop at 70.
        contract = self._contract(5000.0, birthday="1954-02-10")
        slip = self._slip(contract, "2026-11-01", "2026-11-30")
        self._assert_lines(slip, {"CA_CPP": -296.63, "CA_PE": 5000.0})
        # Turns 73 in 2026: no QPP from January 1.
        contract = self._contract(5000.0, birthday="1953-12-31")
        slip = self._slip(contract, "2026-01-01", "2026-01-31")
        self._assert_lines(slip, {"CA_CPP": 0.0, "CA_CPP2": 0.0, "CA_PE": 0.0})

    def test_qpp_starts_after_18(self):
        contract = self._contract(5000.0, birthday="2008-03-10")
        march, april = self._monthly_slips(contract, [3, 4])
        self.assertEqual(self._line(march, "CA_CPP"), 0.0)
        self.assertAlmostEqual(self._line(april, "CA_CPP"), -296.63)

    # ------------------------------------------------------------------
    # Maximums, RL-1, T4 and remittances
    # ------------------------------------------------------------------

    def test_maximums_rl1_t4_and_remittances(self):
        self.company.l10n_ca_qc_remitter_type = "monthly"
        contract = self._contract(15000.0)
        slips = self._monthly_slips(contract, range(1, 9))
        # QPP: 0.063 * (15,000 - 291.66) = 926.63 for months 1-4; month 5:
        #   4,479.30 - 4 * 926.63 = 772.78. QPP2 month 5: (60,000 + 15,000
        #   - 74,600) * 0.04 = 16.00, month 6: 416 - 16 = 400.
        # EI: 195.00 for months 1-4, month 5: 895.70 - 780 = 115.70.
        # QPIP: 64.50 for months 1-6, month 7: 442.90 - 387 = 55.90;
        #   employer 90.30, month 7: 620.06 - 541.80 = 78.26.
        # CNT: 9.00 for months 1-6, month 7: (103,000 - 90,000) * 0.0006
        #   = 7.80, month 8: 0.
        # Quebec tax month 1: H = 120.83, CSA = 926.63 / 6.3 = 147.08,
        #   I = 12 * 14,732.09 = 176,785.08 -> T 0.2575, K 10,465
        #   Y = 45,522.16 - 10,465 - 2,653.28 = 32,403.88 -> 2,700.32
        # Month 5: CSA = 772.78 / 6.3 + 16 = 138.66, I = 176,886.12
        #   -> Y = 32,429.90 -> 2,702.49
        # Month 6: CSA = 400, I = 173,750.04 -> Y = 31,622.36 -> 2,635.20
        # Months 7-8: CSA = 0, I = 178,550.04 -> Y = 32,858.36 -> 2,738.20
        # Federal month 1: A = 12 * (15,000 - 147.08) = 178,234.99, R 0.26
        #   K2 = 0.14 * (3,768.30 + 895.70 + 442.90) = 714.97 (capped)
        #   T3 = 46,341.10 - 10,241 - 2,303.28 - 714.97 - 210.14 = 32,871.71
        #   T1 = 27,447.88 -> 2,287.32. Month 5: A = 178,336.03 -> 2,289.15;
        #   month 6: A = 175,200 -> 2,232.42; months 7-8: 180,000 -> 2,319.26
        cpp = [926.63] * 4 + [772.78, 0.0, 0.0, 0.0]
        cpp2 = [0.0] * 4 + [16.0, 400.0, 0.0, 0.0]
        ei = [195.0] * 4 + [115.70, 0.0, 0.0, 0.0]
        qpip = [64.50] * 6 + [55.90, 0.0]
        qpip_er = [90.30] * 6 + [78.26, 0.0]
        cnt = [9.0] * 6 + [7.80, 0.0]
        qc_tax = [2700.32] * 4 + [2702.49, 2635.20, 2738.20, 2738.20]
        fed_tax = [2287.32] * 4 + [2289.15, 2232.42, 2319.26, 2319.26]
        for index, slip in enumerate(slips):
            self._assert_lines(
                slip,
                {
                    "CA_CPP": -cpp[index],
                    "CA_CPP2": -cpp2[index],
                    "CA_EI": -ei[index],
                    "CA_QPIP": -qpip[index],
                    "CA_QPIP_ER": qpip_er[index],
                    "CA_QC_CNT": cnt[index],
                    "CA_PIT": -qc_tax[index],
                    "CA_FIT": -fed_tax[index],
                    "CA_QC_HSF": 247.50,
                },
            )
        total_qc_tax = sum(qc_tax)
        total_fed_tax = sum(fed_tax)

        # The entry of a Quebec payslip balances on the rule accounts only.
        move = slips[0].move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(
            set(move.line_ids.account_id.mapped("code")),
            {"512110", "512121", "221203", "221206"},
        )
        payable = move.line_ids.filtered(lambda line: line.account_id.code == "221203")
        self.assertAlmostEqual(
            sum(payable.mapped("credit")) - sum(payable.mapped("debit")),
            self._line(slips[0], "NET"),
        )
        # Employer cost: QPP, EI, QPIP, HSF and CNT of January.
        employer = move.line_ids.filtered(lambda line: line.account_id.code == "512121")
        self.assertAlmostEqual(
            sum(employer.mapped("debit")),
            926.63 + 1.4 * 195.0 + 90.30 + 247.50 + 9.0,
        )

        # T4: Quebec boxes, QPP in 17/17A, box 22 without the Quebec tax.
        t4_summary = self.env["l10n_ca.payroll.t4.summary"].create(
            {"company_id": self.company.id, "year": 2026}
        )
        t4_summary.action_compute_slips()
        t4 = t4_summary.slip_ids
        self.assertEqual(t4.province_code, "QC")
        self.assertAlmostEqual(t4.box_17, 4479.30)
        self.assertAlmostEqual(t4.box_17a, 416.0)
        self.assertAlmostEqual(t4.box_16, 0.0)
        self.assertAlmostEqual(t4.box_18, 895.70)
        self.assertAlmostEqual(t4.box_22, total_fed_tax)
        self.assertAlmostEqual(t4.box_24, 68900.0)
        self.assertAlmostEqual(t4.box_26, 85000.0)
        self.assertAlmostEqual(t4.box_55, 442.90)
        self.assertAlmostEqual(t4.box_56, 103000.0)
        rows = t4_summary._l10n_ca_t4_csv_rows()
        position = rows[0].index("56 PPIP insurable earnings")
        self.assertEqual(rows[0][position + 1], "Dental benefits code (45)")
        self.assertEqual(rows[1][position - 1 : position + 1], ["442.90", "103000.00"])

        # RL-1
        summary = self.env["l10n_ca.qc.rl1.summary"].create(
            {"company_id": self.company.id, "year": 2026}
        )
        # February 28, 2027 is a Sunday: due the next Monday.
        self.assertEqual(summary.due_date, date(2027, 3, 1))
        summary.action_compute_slips()
        rl1 = summary.slip_ids
        self.assertEqual(len(rl1), 1)
        self.assertAlmostEqual(rl1.box_a, 120000.0)
        self.assertAlmostEqual(rl1.box_b_a, 4479.30)
        self.assertAlmostEqual(rl1.box_b_b, 416.0)
        self.assertAlmostEqual(rl1.box_c, 895.70)
        self.assertAlmostEqual(rl1.box_e, total_qc_tax)
        # Box G capped at the additional MPE since B.B is filled.
        self.assertAlmostEqual(rl1.box_g, 85000.0)
        self.assertAlmostEqual(rl1.box_h, 442.90)
        self.assertAlmostEqual(rl1.box_i, 103000.0)
        self.assertAlmostEqual(rl1.cnt_base, 103000.0)

        summary.action_compute_remittances()
        remittances = summary.remittance_ids.sorted("date_from")
        self.assertEqual(len(remittances), 8)
        january = remittances[0]
        # February 15, 2026 is a Sunday: due the next Monday.
        self.assertEqual(january.due_date, date(2026, 2, 16))
        # QPP 2 * 926.63, QPIP 64.50 + 90.30, tax 2,700.32, HSF 247.50
        self.assertAlmostEqual(january.qpp, 1853.26)
        self.assertAlmostEqual(january.qpip, 154.80)
        self.assertAlmostEqual(january.income_tax, 2700.32)
        self.assertAlmostEqual(january.total, 1853.26 + 154.80 + 2700.32 + 247.50)

        # RLZ-1.S: lines 25 = 2 * (4,479.30 + 416) = 9,790.60;
        # 29 = 103,000 * 0.00602 = 620.06; HSF 1.65% * 120,000 = 1,980.00;
        # CNT 103,000 * 0.0006 = 61.80. The remittances cover the year,
        # so lines 48 and 57 are 0 and the balance is the CNT.
        self.assertAlmostEqual(summary.line_25, 9790.60)
        self.assertAlmostEqual(summary.line_29, 620.06)
        self.assertAlmostEqual(summary.line_30, 1062.96)
        self.assertAlmostEqual(summary.line_35, total_qc_tax)
        self.assertAlmostEqual(summary.line_48, 0.0)
        self.assertAlmostEqual(summary.line_50_1, 120000.0)
        self.assertAlmostEqual(summary.line_54, 1.65)
        self.assertAlmostEqual(summary.line_55, 1980.0)
        self.assertAlmostEqual(summary.line_57, 0.0)
        self.assertAlmostEqual(summary.line_61, 103000.0)
        self.assertAlmostEqual(summary.line_63, 61.80)
        self.assertAlmostEqual(summary.line_71, 0.0)
        self.assertAlmostEqual(summary.line_82, 61.80)
        summary.cnt_paid = 61.80
        self.assertAlmostEqual(summary.line_80, 0.0)
        # Salaries eligible for an HSF credit: line 53 = 120,000 - 20,000,
        # 55 = 1.65% * 100,000 = 1,650.00, 57 = 1,650 - 1,980 = -330.
        summary.write({"line_52": 20000.0, "line_52_1": "Test project"})
        self.assertAlmostEqual(summary.line_50_1, 120000.0)
        self.assertAlmostEqual(summary.line_53, 100000.0)
        self.assertAlmostEqual(summary.line_55, 1650.0)
        self.assertAlmostEqual(summary.line_57, -330.0)
        self.assertAlmostEqual(summary.line_81, 330.0)

        self.assertTrue(summary.action_export_rl1_csv())
        rows = summary.with_context(lang="en_US")._l10n_ca_qc_rl1_csv_rows()
        self.assertEqual(rows[0][3], "A Employment income")
        self.assertEqual(rows[1][3], "120000.00")
        self.assertIn(
            ["52.1 HSF contribution credit specification", "Test project"], rows
        )
        self.assertIn(["53 Line 51 minus line 52", "100000.00"], rows)
        self.assertTrue(summary.action_export_remittance_csv())

    def test_remittance_periods(self):
        Remittance = self.env["l10n_ca.qc.payroll.remittance"]
        periods = Remittance._l10n_ca_qc_periods
        self.company.l10n_ca_qc_remitter_type = "annual"
        self.assertEqual(
            periods(self.company, 2026),
            [(date(2026, 1, 1), date(2026, 12, 31), date(2027, 1, 15))],
        )
        self.company.l10n_ca_qc_remitter_type = "quarterly"
        result = periods(self.company, 2026)
        self.assertEqual(len(result), 4)
        self.assertEqual(
            result[1], (date(2026, 4, 1), date(2026, 6, 30), date(2026, 7, 15))
        )
        self.company.l10n_ca_qc_remitter_type = "twice_monthly"
        result = periods(self.company, 2026)
        self.assertEqual(len(result), 24)
        # January 25, 2026 is a Sunday: due Monday 26.
        self.assertEqual(
            result[0], (date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 26))
        )
        self.assertEqual(
            result[1], (date(2026, 1, 16), date(2026, 1, 31), date(2026, 2, 10))
        )
        # Without a frequency, the one of the CRA remitter type applies.
        self.company.write(
            {
                "l10n_ca_qc_remitter_type": False,
                "l10n_ca_payroll_remitter_type": "quarterly",
            }
        )
        self.assertEqual(len(periods(self.company, 2026)), 4)
        self.company.l10n_ca_qc_remitter_type = "weekly"
        result = periods(self.company, 2026)
        self.assertEqual(len(result), 48)
        # January 7, 2026 is a Wednesday: third business day -> Monday 12.
        self.assertEqual(
            result[0], (date(2026, 1, 1), date(2026, 1, 7), date(2026, 1, 12))
        )

    def test_due_dates_skip_closure_days(self):
        """Public holidays and Revenu Quebec closures are not business days."""
        Remittance = self.env["l10n_ca.qc.payroll.remittance"]
        # Closure days of the end of 2026, as the Tax Compliance Calendar
        # provides them: December 26 and January 2 fall on a Saturday and
        # move to the Monday.
        closed = {
            date(2026, 12, 24),
            date(2026, 12, 25),
            date(2026, 12, 28),
            date(2026, 12, 31),
            date(2027, 1, 1),
            date(2027, 1, 4),
        }

        def closed_days(self, company, year):
            return {day for day in closed if day.year == year}

        with patch.object(type(Remittance), "_l10n_ca_qc_closed_days", closed_days):
            self.company.l10n_ca_qc_remitter_type = "weekly"
            result = Remittance._l10n_ca_qc_periods(self.company, 2026)
            # Third business day after December 21: 22, 23, then 29.
            self.assertEqual(
                result[-2], (date(2026, 12, 15), date(2026, 12, 21), date(2026, 12, 29))
            )
            # After December 31: January 5, 6 and 7 (TP-1015.G table 8).
            self.assertEqual(
                result[-1], (date(2026, 12, 22), date(2026, 12, 31), date(2027, 1, 7))
            )
            self.company.l10n_ca_qc_remitter_type = "twice_monthly"
            result = Remittance._l10n_ca_qc_periods(self.company, 2026)
            # December 25 is closed, then a weekend and the 28th: the 29th.
            self.assertEqual(
                result[-2], (date(2026, 12, 1), date(2026, 12, 15), date(2026, 12, 29))
            )
            summary = self.env["l10n_ca.qc.rl1.summary"].create(
                {"company_id": self.company.id, "year": 2026}
            )
            self.assertEqual(summary.due_date, date(2027, 3, 1))
            # A last periodic remittance on August 10: due September 20, a
            # Sunday, so September 21.
            summary.last_remittance_date = "2026-08-10"
            self.assertEqual(summary.due_date, date(2026, 9, 21))
            # A cessation on June 15: due 30 days after, July 15.
            summary.cessation_date = "2026-06-15"
            self.assertEqual(summary.due_date, date(2026, 7, 15))

    def test_french_labels(self):
        """Payslip lines and copied selections read in the user language."""
        self.env["res.lang"]._activate_lang("fr_CA")
        self.env["ir.module.module"].search(
            [
                (
                    "name",
                    "in",
                    ("l10n_ca_time_parameter", "l10n_ca_payroll", "l10n_ca_qc_payroll"),
                )
            ]
        )._update_translations(["fr_CA"], overwrite=True)
        self.env = self.env(context=dict(self.env.context, lang="fr_CA"))
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", done=True)
        names = {line.code: line.name for line in slip.line_ids}
        self.assertEqual(names["GROSS"], "Brut")
        self.assertEqual(names["CA_CPP"], "Cotisations au RRQ")
        self.assertEqual(names["CA_CPP_ER"], "Cotisations de l'employeur au RRQ")
        self.assertEqual(names["CA_QC_HSF"], "Fonds des services de santé (1,65 %)")
        self.assertIn("Cotisations au RRQ", slip.move_id.line_ids.mapped("name"))
        remittance = self.env["l10n_ca.qc.payroll.remittance"]
        selection = dict(
            remittance.fields_get(["remitter_type"])["remitter_type"]["selection"]
        )
        self.assertEqual(selection["monthly"], "Mensuel")
        federal = self.env["l10n_ca.payroll.remittance"]
        selection = dict(
            federal.fields_get(["remitter_type"])["remitter_type"]["selection"]
        )
        self.assertEqual(selection["regular"], "Régulier (mensuel)")
        t4_slip = self.env["l10n_ca.payroll.t4.slip"]
        selection = dict(t4_slip.fields_get(["box_45"])["box_45"]["selection"])
        self.assertTrue(selection["1"].startswith("1 - Non admissible"))
        # RL-1 and remittance exports: headers in the language of the user.
        summary = self.env["l10n_ca.qc.rl1.summary"].create(
            {"company_id": self.company.id, "year": 2026}
        )
        summary.action_compute_slips()
        summary.action_compute_remittances()
        rows = summary._l10n_ca_qc_rl1_csv_rows()
        self.assertEqual(
            rows[0][:4], ["Employé", "NAS", "Code du relevé", "A Revenus d'emploi"]
        )
        self.assertEqual(rows[0][4], "B.A Cotisation au RRQ")
        labels = [row[0] for row in rows if row]
        self.assertIn("53 Ligne 51 moins ligne 52", labels)
        self.assertIn("Nombre de relevés 1", labels)
        rows = summary._l10n_ca_qc_remittance_csv_rows()
        self.assertEqual(rows[0][:3], ["Payé du", "Payé au", "Date d'échéance"])
