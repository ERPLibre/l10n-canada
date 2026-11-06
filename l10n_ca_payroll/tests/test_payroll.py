# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Payslips checked against the T4127 formulas (122nd edition, 2026).

Shipped 2026 parameters used by the derivations: YMPE 74,600, YAMPE
85,000, exemption 3,500, CPP rate 5.95% (base 4.95%), CPP2 4%, EI 1.63%
(Quebec 1.30%) up to 68,900, federal brackets 14% / 20.5% from 58,523 /
26% from 117,045 / 29% from 181,440 / 33% from 258,482 (constants K 0,
3,804, 10,241, 15,685, 26,024), BPA 16,452 down to 14,829, CEA 1,501,
credit rate 14%, Quebec abatement 16.5%.
"""

from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.models.hr_payslip import HrPayslip

# Federal K2 items without those a provincial module adds.
FEDERAL_K2_ITEMS = HrPayslip._l10n_ca_federal_k2_items


@tagged("post_install", "-at_install")
class TestCanadianPayroll(AccountTestInvoicingCommon):
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
                "name": "Payroll Test Employee",
                "birthday": birthday,
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Payroll Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": schedule,
                "l10n_ca_province_id": (province or self.ontario).id,
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
        slips = []
        for month in months:
            end = date(2026, month, 28 if month == 2 else 30)
            slips.append(self._slip(contract, date(2026, month, 1), end, done=done))
        return slips

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

    def test_setup_structure_and_accounts(self):
        self.assertEqual(self.structure.code, "CA_BASE")
        self.assertEqual(self.structure.company_id, self.company)
        self.assertEqual(self.company.chart_template, "ca_2023")
        rule = self.env.ref("l10n_ca_payroll.rule_gross").with_company(self.company)
        self.assertEqual(rule.account_debit.code, "512110")
        self.assertEqual(rule.account_credit.code, "221203")
        employer = self.env.ref("l10n_ca_payroll.rule_ei_employer").with_company(
            self.company
        )
        self.assertEqual(employer.account_credit.code, "221206")
        # A second call keeps the structure and the accounts in place.
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(self.company._l10n_ca_payroll_structure(), self.structure)

    # ------------------------------------------------------------------
    # Federal computation, outside Quebec
    # ------------------------------------------------------------------

    def test_monthly_ontario(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # P = 12, I = 5,000. Exemption 3,500 / 12 = 291.66 (truncated).
        # C = 0.0595 * (5,000 - 291.66) = 280.146 -> 280.15
        # C2: W = 74,600; 0 + 5,000 - 74,600 < 0 -> 0
        # EI = 0.0163 * 5,000 = 81.50; employer 1.4 * 81.50 = 114.10
        # F5A = 280.15 * 0.01 / 0.0595 = 47.0840
        # A = 12 * (5,000 - 47.0840) = 59,434.99 -> R 0.205, K 3,804
        # K1 = 0.14 * 16,452 = 2,303.28
        # K2 = 0.14 * (12 * 280.15 * 0.0495 / 0.0595) + 0.14 * (12 * 81.50)
        #    = 0.14 * 2,796.79 + 0.14 * 978 = 528.47
        # K4 = 0.14 * 1,501 = 210.14
        # T3 = 0.205 * 59,434.99 - 3,804 - 2,303.28 - 528.47 - 210.14
        #    = 5,338.28 -> per pay 444.86
        self._assert_lines(
            slip,
            {
                "BASIC": 5000.0,
                "GROSS": 5000.0,
                "CA_CPP": -280.15,
                "CA_CPP2": 0.0,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": 0.0,
                "NET": 5000.0 - 280.15 - 81.50 - 444.86,
                "CA_CPP_ER": 280.15,
                "CA_EI_ER": 114.10,
            },
        )
        self.assertEqual(slip.l10n_ca_pension_plan, "cpp")
        self.assertEqual(slip.l10n_ca_province_id, self.ontario)

    def test_provincial_tax_warning(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("NOT COMPUTED", line.name)
        self.assertIn(self.ontario.name, slip.l10n_ca_warning)

    def test_biweekly(self):
        contract = self._contract(5200.0, schedule="bi-weekly")
        self.assertEqual(contract.l10n_ca_pay_periods, 26)
        slip = self._slip(contract, "2026-03-02", "2026-03-15")
        # Wage 5,200 / month -> 5,200 * 12 / 26 = 2,400 per pay.
        # Exemption 3,500 / 26 = 134.61. C = 0.0595 * 2,265.39 = 134.79
        # EI = 0.0163 * 2,400 = 39.12
        # A = 26 * (2,400 - 134.79 * 0.01 / 0.0595) = 61,811.00
        # K2 = 0.14 * (26 * 134.79 * 0.0495 / 0.0595) + 0.14 * (26 * 39.12)
        #    = 550.57
        # T3 = 0.205 * 61,811.00 - 3,804 - 2,303.28 - 550.57 - 210.14
        #    = 5,803.26 -> per pay 5,803.26 / 26 = 223.20
        self._assert_lines(
            slip,
            {
                "BASIC": 2400.0,
                "CA_CPP": -134.79,
                "CA_EI": -39.12,
                "CA_FIT": -223.20,
                "CA_EI_ER": 54.77,
            },
        )

    def test_low_income_no_tax(self):
        contract = self._contract(1000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.0595 * (1,000 - 291.66) = 42.15; EI = 16.30
        # A = 11,914.99: 0.14 * A = 1,668.10 < K1 (2,303.28) -> T3 = 0
        self._assert_lines(slip, {"CA_CPP": -42.15, "CA_EI": -16.30, "CA_FIT": 0.0})

    def test_basic_personal_amount_phase_out(self):
        contract = self._contract(25000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # C = 0.0595 * (25,000 - 291.66) = 1,470.15; EI = 407.50
        # A = 12 * (25,000 - 1,470.15 * 0.01 / 0.0595) = 297,034.99
        #   -> R 0.33, K 26,024; A >= 258,482 -> BPA 14,829, K1 2,076.06
        # K2 = 0.14 * 3,519.45 + 0.14 * 1,123.07 = 649.95 (both capped)
        # T3 = 0.33 * 297,034.99 - 26,024 - 2,076.06 - 649.95 - 210.14
        #    = 69,061.39 -> per pay 5,755.12
        self._assert_lines(slip, {"CA_CPP": -1470.15, "CA_FIT": -5755.12})

    def test_td1_claim_and_additional_tax(self):
        contract = self._contract(
            5000.0,
            l10n_ca_td1_federal_type="custom",
            l10n_ca_td1_federal_amount=0.0,
            l10n_ca_additional_federal_tax=50.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # Claim code 0: K1 = 0, T3 = 5,338.28 + 2,303.28 = 7,641.56
        # -> 636.80 per pay, plus 50.00 requested on the TD1.
        self._assert_lines(slip, {"CA_FIT": -686.80})

    def test_exemptions(self):
        contract = self._contract(
            5000.0, l10n_ca_cpp_exempt=True, l10n_ca_ei_exempt=True
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # No CPP and no EI: A = 60,000, K2 = 0
        # T3 = 0.205 * 60,000 - 3,804 - 2,303.28 - 210.14 = 5,982.58
        # -> per pay 498.55
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": 0.0,
                "CA_EI": 0.0,
                "CA_PE": 0.0,
                "CA_IE": 0.0,
                "CA_FIT": -498.55,
            },
        )

    # ------------------------------------------------------------------
    # Year-to-date maximums, accounting, T4 and remittances
    # ------------------------------------------------------------------

    def test_maximums_t4_and_remittances(self):
        self.company.l10n_ca_payroll_remitter_type = "regular"
        contract = self._contract(15000.0)
        slips = self._monthly_slips(contract, range(1, 8))
        # Months 1-4: C = 0.0595 * (15,000 - 291.66) = 875.15, EI 244.50.
        # Month 5: C = 4,230.45 - 4 * 875.15 = 729.85; EI = 1,123.07 - 978
        #   = 145.07; C2: W = 74,600, (60,000 + 15,000 - 74,600) * 0.04 = 16
        # Month 6: C = 0, EI = 0, C2 = min(416 - 16, 15,000 * 0.04) = 400
        # Month 7: C2 = 0, all maximums reached.
        # Tax months 1-4: A = 12 * (15,000 - 147.08) = 178,234.99
        #   R 0.26, K 10,241, K2 = 0.14 * (3,519.45 + 1,123.07) = 649.95
        #   T3 = 46,341.10 - 10,241 - 2,303.28 - 649.95 - 210.14
        #      = 32,936.73 -> 2,744.73
        # Month 5: A = 12 * (15,000 - 729.85 / 5.95 - 16) = 178,336.03
        #   -> T3 = 32,963.00 -> 2,746.92
        # Month 6: A = 12 * (15,000 - 400) = 175,200; the maxima are
        #   reached, so K2 keeps 649.95 -> T3 = 32,147.63 -> 2,678.97
        # Month 7: A = 180,000 -> T3 = 33,395.63 -> 2,782.97
        cpp = [875.15] * 4 + [729.85, 0.0, 0.0]
        cpp2 = [0.0] * 4 + [16.0, 400.0, 0.0]
        ei = [244.50] * 4 + [145.07, 0.0, 0.0]
        tax = [2744.73] * 4 + [2746.92, 2678.97, 2782.97]
        for index, slip in enumerate(slips):
            self._assert_lines(
                slip,
                {
                    "CA_CPP": -cpp[index],
                    "CA_CPP2": -cpp2[index],
                    "CA_EI": -ei[index],
                    "CA_FIT": -tax[index],
                },
            )
        # Each done payslip posts a balanced entry.
        move = slips[0].move_id
        self.assertEqual(move.state, "posted")
        self.assertAlmostEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )
        expense = move.line_ids.filtered(lambda line: line.account_id.code == "512110")
        self.assertAlmostEqual(expense.debit, 15000.0)
        # Every line lands on a rule account: no balancing line on the
        # default account of the journal.
        self.assertEqual(
            set(move.line_ids.account_id.mapped("code")),
            {"512110", "512121", "221203", "221206"},
        )
        # Wages payable: gross less the employee deductions, i.e. the net.
        payable = move.line_ids.filtered(lambda line: line.account_id.code == "221203")
        self.assertAlmostEqual(
            sum(payable.mapped("credit")) - sum(payable.mapped("debit")),
            self._line(slips[0], "NET"),
        )
        # Source deductions payable: employee and employer shares.
        remit = move.line_ids.filtered(lambda line: line.account_id.code == "221206")
        self.assertAlmostEqual(
            sum(remit.mapped("credit")) - sum(remit.mapped("debit")),
            2 * 875.15 + 244.50 + 342.30 + 2744.73,
        )

        summary = self.env["l10n_ca.payroll.t4.summary"].create(
            {"company_id": self.company.id, "year": 2026}
        )
        summary.action_compute_slips()
        t4 = summary.slip_ids
        self.assertEqual(len(t4), 1)
        self.assertEqual(t4.province_code, "ON")
        self.assertAlmostEqual(t4.box_14, 105000.0)
        self.assertAlmostEqual(t4.box_16, 4230.45)
        self.assertAlmostEqual(t4.box_16a, 416.0)
        self.assertAlmostEqual(t4.box_18, 1123.07)
        self.assertAlmostEqual(t4.box_22, 4 * 2744.73 + 2746.92 + 2678.97 + 2782.97)
        # Box 24 capped at the MIE (68,900), box 26 at the YAMPE (85,000).
        self.assertAlmostEqual(t4.box_24, 68900.0)
        self.assertAlmostEqual(t4.box_26, 85000.0)
        # Employer EI 4 * 342.30 + 203.10 = 1,572.30, the 2026 maximum.
        self.assertAlmostEqual(summary.line_19, 1572.30)
        self.assertAlmostEqual(summary.line_27, 4230.45)
        self.assertAlmostEqual(summary.line_27a, 416.0)
        self.assertEqual(summary.line_88, 1)
        self.assertEqual(summary.due_date, date(2027, 2, 28))
        self.assertAlmostEqual(
            summary.line_80,
            2 * 4230.45 + 2 * 416.0 + 1123.07 + 1572.30 + t4.box_22,
        )

        summary.action_compute_remittances()
        remittances = summary.remittance_ids.sorted("date_from")
        self.assertEqual(len(remittances), 7)
        january = remittances[0]
        # February 15, 2026 is a Sunday: due the next Monday.
        self.assertEqual(january.due_date, date(2026, 2, 16))
        # 2 * 875.15 + 244.50 + 342.30 + 2,744.73 = 5,081.83
        self.assertAlmostEqual(january.total, 5081.83)
        self.assertEqual(january.employee_count, 1)
        january.amount_paid = 5081.83
        self.assertAlmostEqual(summary.line_82, 5081.83)
        self.assertAlmostEqual(summary.line_86, summary.line_80 - 5081.83)

        action = summary.action_export_t4_csv()
        self.assertIn("csv_file", action["url"])
        self.assertTrue(summary.csv_file)
        rows = summary._l10n_ca_t4_csv_rows()
        self.assertEqual(rows[1][2], "ON")
        self.assertEqual(rows[1][3], "105000.00")
        self.assertEqual(t4.box_45, "1")
        self.assertEqual(rows[1][-3], "1")
        self.assertTrue(summary.action_export_pd7a_csv())

    def test_refund_reduces_year_to_date(self):
        contract = self._contract(15000.0)
        first = self._monthly_slips(contract, [1])[0]
        first.refund_sheet()
        second = self._slip(contract, "2026-02-01", "2026-02-28")
        # The refund cancels January: February is again a first pay.
        self._assert_lines(second, {"CA_CPP": -875.15, "CA_EI": -244.50})

    # ------------------------------------------------------------------
    # Age limits of the CPP
    # ------------------------------------------------------------------

    def test_cpp_stops_at_70(self):
        # Turns 70 in March 2026: PM = 3, maximum 4,230.45 * 3 / 12 =
        # 1,057.61. January 875.15, February 1,057.61 - 875.15 = 182.46,
        # March 0 (maximum reached), April not pensionable.
        contract = self._contract(15000.0, birthday="1956-03-10")
        slips = self._monthly_slips(contract, [1, 2, 3, 4])
        self.assertEqual(
            [-self._line(s, "CA_CPP") for s in slips], [875.15, 182.46, 0.0, 0.0]
        )
        self.assertEqual(self._line(slips[3], "CA_PE"), 0.0)
        self.assertAlmostEqual(self._line(slips[2], "CA_PE"), 15000.0)

    def test_cpp_starts_after_18(self):
        # Turns 18 in March 2026: contributions start with the April pay.
        contract = self._contract(5000.0, birthday="2008-03-10")
        march, april = self._monthly_slips(contract, [3, 4])
        self.assertEqual(self._line(march, "CA_CPP"), 0.0)
        self.assertAlmostEqual(self._line(april, "CA_CPP"), -280.15)

    # ------------------------------------------------------------------
    # Bonuses and other non-periodic payments
    # ------------------------------------------------------------------

    def test_bonus_example_t4127(self):
        """Regular bonus calculation example of T4127: TB = 323.54.

        1,000 a week, a bonus of 1,500 paid earlier in the year (F5BYTD
        14.60) and a bonus of 2,500 payable now.
        """
        # 4,333.33 * 12 / 52 = 1,000.00 a week.
        contract = self._contract(4333.33, schedule="weekly")
        earlier = self._slip(
            contract, "2026-02-02", "2026-02-08", done=True, bonus=1500.0
        )
        # C = 0.0595 * (2,500 - 67.30) = 144.75, F5 = 144.75 / 5.95 = 24.33
        # F5B = 24.33 * 1,500 / 2,500 = 14.60, as in the example.
        self._assert_lines(
            earlier, {"GROSS": 2500.0, "CA_NPP": 1500.0, "CA_F5B": 14.60}
        )
        slip = self._slip(contract, "2026-07-20", "2026-07-26", bonus=2500.0)
        # C = 0.0595 * (3,500 - 67.30) = 204.25, F5 = 34.3277,
        # F5A = 34.3277 * 1,000 / 3,500 = 9.81, F5B = 24.52
        # EI = 0.0163 * 3,500 = 57.05
        # Regular pay: A = 52 * (1,000 - 9.8079) = 51,489.99
        #   K2 = 0.14 * (52 * 55.50 * 4.95 / 5.95) + 0.14 * (52 * 16.30)
        #      = 454.80
        #   T3 = 0.14 * 51,489.99 - 2,303.28 - 454.80 - 210.14 = 4,240.38
        #   -> 81.55
        # TB: A with = 51,489.99 + (2,500 - 24.52) + (1,500 - 14.60);
        #   K2 adds 0.14 * (123.75 * 4.95 / 5.95 + 40.75) = 23.03;
        #   TB = 0.14 * 2,475.48 - 23.03 = 323.54
        self._assert_lines(
            slip,
            {
                "CA_BONUS": 2500.0,
                "GROSS": 3500.0,
                "CA_CPP": -204.25,
                "CA_EI": -57.05,
                "CA_NPP": 2500.0,
                "CA_F5B": 24.52,
                "CA_FIT": -(81.55 + 323.54),
            },
        )

    def test_bonus_flat_rate(self):
        """A at most 5,000 with the bonus: 15% of the bonus, 10% in Quebec."""
        contract = self._contract(200.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", bonus=1000.0)
        # A = 12 * 200 + 1,000 less the additional contributions < 5,000;
        # the regular pay of 200 bears no federal tax.
        self._assert_lines(slip, {"GROSS": 1200.0, "CA_FIT": -150.0})
        self._qpp_parameters()
        contract = self._contract(200.0, province=self.quebec)
        slip = self._slip(contract, "2026-03-01", "2026-03-31", bonus=1000.0)
        self._assert_lines(slip, {"CA_FIT": -100.0})

    def test_bonus_leaves_the_regular_pay_unchanged(self):
        """Without bonus input, the pay is the regular pay of the contract."""
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self.assertFalse(slip.line_ids.filtered(lambda line: line.code == "CA_BONUS"))
        self._assert_lines(slip, {"GROSS": 5000.0, "CA_NPP": 0.0, "CA_F5B": 0.0})

    # ------------------------------------------------------------------
    # Quebec employee: QPP rates and federal abatement
    # ------------------------------------------------------------------

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

    def test_quebec_federal_abatement(self):
        self._qpp_parameters()
        contract = self._contract(5000.0, province=self.quebec)
        # The extension point is neutralised so that the federal formula is
        # checked alone, whether or not a Quebec module adds a QPIP credit.
        with patch.object(
            type(self.env["hr.payslip"]),
            "_l10n_ca_federal_k2_items",
            FEDERAL_K2_ITEMS,
        ):
            slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # QPP C = 0.063 * (5,000 - 291.66) = 296.63; EI = 0.013 * 5,000 = 65
        # F5A = 296.63 * 0.01 / 0.063 = 47.0841; A = 59,434.99
        # K2 = 0.14 * (12 * 296.63 * 0.053 / 0.063) + 0.14 * (12 * 65)
        #    = 0.14 * 2,994.55 + 0.14 * 780 = 528.44
        # T3 = 0.205 * 59,434.99 - 3,804 - 2,303.28 - 528.44 - 210.14
        #    = 5,338.32; T1 = T3 * (1 - 0.165) = 4,457.49 -> 371.46
        self._assert_lines(
            slip,
            {
                "CA_CPP": -296.63,
                "CA_EI": -65.0,
                "CA_FIT": -371.46,
                "CA_CPP_ER": 296.63,
                "CA_EI_ER": 91.0,
            },
        )
        self.assertEqual(slip.l10n_ca_pension_plan, "qpp")
        cpp_line = slip.line_ids.filtered(lambda line: line.code == "CA_CPP")
        self.assertEqual(cpp_line.name, "QPP Contributions")

    def test_quebec_k2_extension_point(self):
        """The QPIP credit of the Quebec module enters K2 through the hook."""
        self._qpp_parameters()
        contract = self._contract(5000.0, province=self.quebec)

        def qpip_items(payslip, vals):
            # QPIP 2026: 0.43% up to a maximum premium of 442.90.
            items = FEDERAL_K2_ITEMS(payslip, vals)
            items["qpip"] = {
                "period": vals["gross"] * 0.0043,
                "reached": False,
                "maximum": 442.90,
            }
            return items

        with patch.object(
            type(self.env["hr.payslip"]), "_l10n_ca_federal_k2_items", qpip_items
        ):
            slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # K2 += 0.14 * 12 * 21.50 = 36.12 -> T3 = 5,302.20,
        # T1 = 4,427.33 -> 368.94
        self._assert_lines(slip, {"CA_FIT": -368.94})

    def test_transfer_from_cpp_to_qpp(self):
        """CPP withheld before a transfer to Quebec counts against the QPP.

        TP-1015.F: C = min(4,479.30 * PM/12 - [R * (0.0630 / 0.0595) + A5],
        0.0630 * [S3 - 3,500 / P]) and C2 = min(416 * PM/12 - [R2 *
        (0.04 / 0.04) + A8], 0.04 * (S5 + S3 - W)), S5 and W on the QPP
        salary only.
        """
        self._qpp_parameters()
        # January in Ontario: CPP = 0.0595 * (40,000 - 291.66) = 2,362.65.
        # February in Quebec: R converted = 2,362.65 * 0.063 / 0.0595
        #   = 2,501.6294 -> 2,501.63; C = min(4,479.30 - 2,501.63 =
        #   1,977.67, 0.063 * 39,708.34 = 2,501.63) = 1,977.67; C2: S5 = 0,
        #   40,000 - 74,600 < 0 -> 0.
        # March: C = 4,479.30 - 2,501.63 - 1,977.67 = 0; C2 = min(416,
        #   0.04 * (40,000 + 40,000 - 74,600) = 216) = 216.
        contract = self._contract(40000.0)
        ontario = self._monthly_slips(contract, [1])
        contract.l10n_ca_province_id = self.quebec
        quebec = self._monthly_slips(contract, [2, 3])
        self.assertEqual(ontario[0].l10n_ca_pension_plan, "cpp")
        self._assert_lines(ontario[0], {"CA_CPP": -2362.65, "CA_CPP2": 0.0})
        self.assertEqual(quebec[0].l10n_ca_pension_plan, "qpp")
        self._assert_lines(
            quebec[0], {"CA_CPP": -1977.67, "CA_CPP2": 0.0, "CA_CPP_ER": 1977.67}
        )
        self._assert_lines(quebec[1], {"CA_CPP": 0.0, "CA_CPP2": -216.0})

        # January-February in Ontario: CPP 2,362.65 + 1,867.80 = 4,230.45,
        #   the maximum; CPP2 in February = 0.04 * (80,000 - 74,600) = 216.
        # March in Quebec: R converted = 4,230.45 * 0.063 / 0.0595
        #   = 4,479.30 -> C = 0; C2: 40,000 - 74,600 < 0 -> 0.
        # April: C2 = min(416 - [216 * 0.04 / 0.04 + 0] = 200, 216) = 200.
        # May: C2 = 416 - (216 + 200) = 0.
        contract = self._contract(40000.0)
        ontario = self._monthly_slips(contract, [1, 2])
        contract.l10n_ca_province_id = self.quebec
        quebec = self._monthly_slips(contract, [3, 4, 5])
        self._assert_lines(ontario[1], {"CA_CPP": -1867.80, "CA_CPP2": -216.0})
        self.assertEqual(
            [-self._line(slip, "CA_CPP") for slip in quebec], [0.0, 0.0, 0.0]
        )
        self.assertEqual(
            [-self._line(slip, "CA_CPP2") for slip in quebec], [0.0, 200.0, 0.0]
        )
        self._assert_lines(quebec[1], {"CA_CPP2_ER": 200.0})

    def test_quebec_without_qpp_rates(self):
        if self.company._l10n_ca_param(
            "l10n_ca.qpp.rate", date(2026, 3, 31), default=None
        ):
            self.skipTest("QPP rates provided by an installed module")
        contract = self._contract(5000.0, province=self.quebec)
        with self.assertRaises(UserError):
            self._slip(contract, "2026-03-01", "2026-03-31")

    # ------------------------------------------------------------------
    # Remittance periods
    # ------------------------------------------------------------------

    def test_remittance_periods(self):
        Remittance = self.env["l10n_ca.payroll.remittance"]
        self.company.l10n_ca_payroll_remitter_type = "quarterly"
        periods = Remittance._l10n_ca_periods(self.company, 2026)
        self.assertEqual(len(periods), 4)
        self.assertEqual(
            periods[0], (date(2026, 1, 1), date(2026, 3, 31), date(2026, 4, 15))
        )
        self.assertEqual(periods[3][2], date(2027, 1, 15))

        self.company.l10n_ca_payroll_remitter_type = "accelerated_1"
        periods = Remittance._l10n_ca_periods(self.company, 2026)
        self.assertEqual(len(periods), 24)
        # January 25, 2026 is a Sunday: due Monday 26.
        self.assertEqual(
            periods[0], (date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 26))
        )
        self.assertEqual(
            periods[1], (date(2026, 1, 16), date(2026, 1, 31), date(2026, 2, 10))
        )

        self.company.l10n_ca_payroll_remitter_type = "regular"
        periods = Remittance._l10n_ca_periods(self.company, 2026)
        # August 15, 2026 is a Saturday and November 15 a Sunday.
        self.assertEqual(periods[6][2], date(2026, 8, 17))
        self.assertEqual(periods[9][2], date(2026, 11, 16))
        self.assertEqual(periods[11][2], date(2027, 1, 15))

        self.company.l10n_ca_payroll_remitter_type = "accelerated_2"
        periods = Remittance._l10n_ca_periods(self.company, 2026)
        self.assertEqual(len(periods), 48)
        # January 7, 2026 is a Wednesday: three working days -> Monday 12.
        self.assertEqual(
            periods[0], (date(2026, 1, 1), date(2026, 1, 7), date(2026, 1, 12))
        )
        # January 31, 2026 is a Saturday -> Wednesday, February 4.
        self.assertEqual(
            periods[3], (date(2026, 1, 22), date(2026, 1, 31), date(2026, 2, 4))
        )

    def test_remittance_counts_each_payroll(self):
        """The PD7A counts the last pay period of each pay frequency."""
        self.company.l10n_ca_payroll_remitter_type = "regular"
        monthly = self._contract(6000.0)
        biweekly = self._contract(5200.0, schedule="bi-weekly")
        self._slip(biweekly, "2026-03-02", "2026-03-15", done=True)
        self._slip(biweekly, "2026-03-16", "2026-03-29", done=True)
        self._slip(monthly, "2026-03-01", "2026-03-31", done=True)
        remittance = self.env["l10n_ca.payroll.remittance"]._l10n_ca_generate(
            self.company, 2026
        )
        self.assertEqual(len(remittance), 1)
        self.assertEqual(remittance.payslip_count, 3)
        # Last monthly pay on March 31, last bi-weekly pay on March 29.
        self.assertEqual(remittance.employee_count, 2)
        self.assertEqual(remittance.remitter_type, "regular")
