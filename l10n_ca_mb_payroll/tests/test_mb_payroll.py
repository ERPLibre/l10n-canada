# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Manitoba payslips checked against the T4127 formulas (option 1) and
the step-by-step examples of the T4032 for Manitoba, January 2026.

Shipped 2026 parameters used by the derivations: rates 10.8% / 12.75%
from 47,000 (KP 917) / 17.4% from 100,000 (KP 5,567); BPAMB 15,780 up to
an annual income of 200,000, 15,780 - (NI - 200,000) x 0.0789 up to
400,000 and 0 from there (K1P = 0.108 x 15,780 = 1,704.24 below
200,000); LCP 15% of the shares withheld, at most 1,800; levy 4.3% /
2.15% above 5,000,000, exemption 2,500,000 up to 5,000,000; WCB Manitoba
maximum assessable earnings 171,500. The federal amounts are those of the
tests of l10n_ca_payroll: at 5,000 a month, C = 280.15, EI = 81.50, F5 =
280.15 x 0.01 / 0.0595 = 47.08 rounded to the cent, A = 12 x (5,000 -
47.08) = 59,435.04, T1 = 0.205 x 59,435.04 - 3,804 - 2,303.28 - 528.47 -
210.14 = 5,338.29 and 444.86 of federal tax.

K2P = 0.108 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest Manitoba rate.
"""

from datetime import date
from functools import partial
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page


@tagged("post_install", "-at_install")
class TestManitobaPayroll(AccountTestInvoicingCommon):
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
        cls.manitoba = cls.env.ref("base.state_ca_mb")
        cls.journal = cls.company_data["default_journal_misc"]
        # A rate basis under the exemption: the pays of the tests stay
        # exempt from the levy, without the warning of a basis left at 0.
        cls.account = cls.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": cls.company.id,
                "province_id": cls.manitoba.id,
                "employer_tax_previous_payroll": 150000.0,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Manitoba Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Manitoba Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.manitoba.id,
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
            {"CA_MB_SAL", "CA_MB_WCB_IE", "CA_MB_ER_TAX", "CA_MB_WCB"} <= codes
        )
        for xmlid in ("rule_mb_employer_tax", "rule_mb_wcb"):
            rule = self.env.ref(f"l10n_ca_mb_payroll.{xmlid}").with_company(
                self.company
            )
            self.assertEqual(rule.account_debit.code, "512121", xmlid)
            self.assertEqual(rule.account_credit.code, "221206", xmlid)
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)
        self.assertTrue(self.account.has_employer_tax)

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        self.assertTrue(contract.l10n_ca_prov_computed)
        self.assertEqual(contract.l10n_ca_prov_bpa, 15780.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,435.04 > 47,000 -> V 0.1275, KP 917; BPAMB 15,780
        #   K2P = 0.108 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.108 x (2,796.79 + 978) = 407.68
        #   T4 = 0.1275 x 59,435.04 - 917 - 1,704.24 - 407.68 = 4,549.05
        # (5,338.29 + 4,549.05) / 12 = 823.945 -> 823.95, of which 444.86
        # federal and 379.09 Manitoba.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -379.09,
                "CA_MB_SAL": 5000.0,
                "CA_MB_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("MB", tax_line.name)
        # Remuneration under the exemption: no levy line; no WCB rate: no
        # premium line.
        codes = slip.line_ids.mapped("code")
        self.assertNotIn("CA_MB_ER_TAX", codes)
        self.assertNotIn("CA_MB_WCB", codes)
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 823.95)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Manitoba, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84. The CRA gives 5,957.85
        of federal tax and 4,923.92 of Manitoba tax for the year:
        10,881.77 / 52 = 209.26, of which 114.57 federal and 94.69
        Manitoba.
        """
        # 5,633.33 x 12 / 52 = 1,300.00 a week.
        # T4 = 0.1275 x 62,798.84 - 917 - 1,704.24
        #      - 0.108 x (52 x 73.35 x 0.0495 / 0.0595 + 52 x 21.19)
        #    = 8,006.85 - 917 - 1,704.24 - 461.70 = 4,923.91
        # (5,957.85 + 4,923.91) / 52 = 209.26 -> 209.26 - 114.57 = 94.69
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
                "CA_PIT": -94.69,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Manitoba: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872. The CRA gives 9,406.39 federal and 7,061.05
        Manitoba for the year: 16,467.44 / 52 = 316.68, of which 180.89
        federal and 135.79 Manitoba.
        """
        # 6,933.33 x 12 / 52 = 1,600.00 a week.
        # K2P = 0.108 x (3,519.45 + 1,123.07) = 501.39, the yearly maximums
        # T4 = 0.1275 x 79,872 - 917 - 1,704.24 - 501.39 = 7,061.05
        # (9,406.39 + 7,061.05) / 52 = 316.68 -> 316.68 - 180.89 = 135.79
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
                "CA_PIT": -135.79,
            },
        )

    def test_basic_personal_amount_by_income(self):
        """BPAMB in its three zones, with the rounding of T4127."""
        bpa = partial(
            self.env["hr.payslip"]._l10n_ca_prov_bpa,
            {"company": self.company, "date": date(2026, 3, 31)},
            "l10n_ca.mb",
        )
        self.assertEqual(bpa(59434.99), 15780.0)
        self.assertEqual(bpa(200000.0), 15780.0)
        # 15,780 - 100,000 x (15,780 / 200,000) = 15,780 - 7,890 = 7,890
        self.assertAlmostEqual(bpa(300000.0), 7890.0, places=2)
        # 15,780 - 0.15 x 0.0789 = 15,779.988165: the third decimal 8 rounds
        # the second up, 15,779.99 (a truncation would give 15,779.98).
        self.assertAlmostEqual(bpa(200000.15), 15779.99, places=2)
        # 15,780 - 1 x 0.0789 = 15,779.9211: the third decimal 1 is dropped.
        self.assertAlmostEqual(bpa(200001.0), 15779.92, places=2)
        # 15,780 - 199,999.99 x 0.0789 = 0.000789 -> 0.00
        self.assertAlmostEqual(bpa(399999.99), 0.0, places=2)
        self.assertEqual(bpa(400000.0), 0.0)
        self.assertEqual(bpa(450000.0), 0.0)

    def test_basic_personal_amount_phased_out_on_a_pay(self):
        """25,000 a month without CPP and EI: A = 12 x 25,000 = 300,000."""
        contract = self._contract(
            25000.0, l10n_ca_cpp_exempt=True, l10n_ca_ei_exempt=True
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # Federal: R 0.33, K 26,024; BPAF minimum 14,829 (A >= 258,482);
        #   T3 = 0.33 x 300,000 - 26,024 - 0.14 x 14,829 - 0.14 x 1,501
        #      = 99,000 - 26,024 - 2,076.06 - 210.14 = 70,689.80
        #   70,689.80 / 12 = 5,890.82
        # Manitoba: V 0.174, KP 5,567; BPAMB = 7,890, K1P = 852.12, K2P = 0
        #   T4 = 0.174 x 300,000 - 5,567 - 852.12 = 45,780.88
        # (70,689.80 + 45,780.88) / 12 = 9,705.89 -> 9,705.89 - 5,890.82
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_EI": 0.0,
                "CA_FIT": -5890.82,
                "CA_PIT": -3815.07,
            },
        )
        vals = slip._l10n_ca_compute(contract, 25000.0)
        self.assertAlmostEqual(vals["provincial_annual_income"], 300000.0)
        self.assertAlmostEqual(vals["provincial_basic_tax"], 45780.88)

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1MB claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.1275 x 59,435.04 - 917 - 407.68 - 120 = 6,133.29
        # (5,338.29 + 6,133.29) / 12 = 955.965 -> 955.97 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -531.11})

    def test_labour_sponsored_funds_credit(self):
        # 100 of shares a month: LCP = min(1,800, 15% x 100) = 15 a pay,
        # P x LCP = 180 for the year: T2 = 4,549.05 - 180 = 4,369.05 and
        # (5,338.29 + 4,369.05) / 12 = 808.945 -> 808.95 -> 364.09 Manitoba.
        contract = self._contract(5000.0, l10n_ca_lsvcc_amount=100.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(
            slip,
            {
                "CA_LSVCC": -100.0,
                "CA_FIT": -444.86,
                "CA_PIT": -364.09,
                "NET": 5000.0 - 100.0 - 280.15 - 81.50 - 444.86 - 364.09,
            },
        )
        # 2,000 a month reaches the maximum of the year: 12 x 300 > 1,800.
        contract.l10n_ca_lsvcc_amount = 2000.0
        vals = slip._l10n_ca_compute(contract, 5000.0)
        self.assertAlmostEqual(vals["provincial_lcp"], 1800.0)

    # ------------------------------------------------------------------
    # Health and Post Secondary Education Tax Levy
    # ------------------------------------------------------------------

    def test_levy_rate_and_exemption(self):
        """The engine's rate and exemption give the three cases of the Act."""
        day = date(2026, 6, 30)
        rate = partial(
            self.account._l10n_ca_employer_tax_rate, self.company, "l10n_ca.mb"
        )
        exemption = partial(
            self.account._l10n_ca_employer_tax_exemption, self.company, "l10n_ca.mb"
        )
        # Up to 5,000,000 included: 4.3% of the remuneration above
        # 2,500,000; above it: 2.15% of the whole remuneration.
        self.assertEqual(rate(0.0, day), 0.043)
        self.assertEqual(rate(2500000, day), 0.043)
        self.assertEqual(rate(5000000, day), 0.043)
        self.assertEqual(rate(5000000.01, day), 0.0215)
        self.assertEqual(exemption(2500000, day), 2500000)
        self.assertEqual(exemption(5000000, day), 2500000)
        self.assertEqual(exemption(5000000.01, day), 0.0)
        # The annual levy of each case, rate x (R - exemption):
        # R = 2,500,000 -> 0; R = 4,000,000 -> 4.3% x 1,500,000 = 64,500;
        # R = 5,000,000 -> 107,500 = 2.15% x 5,000,000, the notch meeting
        # the basic rate; R = 6,000,000 -> 2.15% x 6,000,000 = 129,000.
        for total, levy in (
            (2500000, 0.0),
            (4000000, 64500.0),
            (5000000, 107500.0),
            (6000000, 129000.0),
        ):
            self.assertAlmostEqual(
                rate(total, day) * max(0.0, total - exemption(total, day)),
                levy,
                places=2,
                msg=total,
            )
        # No 2027 amendment: the 2026 amounts of the Act stand.
        param = self.company._l10n_ca_param
        self.assertEqual(
            param("l10n_ca.mb.employer_tax.exemption", date(2027, 6, 1)), 2500000
        )

    def test_levy_notch_across_the_exemption(self):
        """A total remuneration of 5,000,000 paid in five pays of 1,000,000."""
        self.account.employer_tax_previous_payroll = 5000000.0
        contract = self._contract(1000000.0)
        slips = self._monthly_slips(contract, range(1, 6))
        # Rate 4.3%, exemption 2,500,000. Paid before the pay R:
        # January R 0 and February R 1,000,000: under the exemption, 0;
        # March R 2,000,000: 3,000,000 - 2,500,000 = 500,000 x 4.3% = 21,500;
        # April and May: the whole 1,000,000 x 4.3% = 43,000.
        # Year: 107,500 = 4.3% x (5,000,000 - 2,500,000).
        self.assertEqual(
            [self._line(s, "CA_MB_ER_TAX") for s in slips],
            [0.0, 0.0, 21500.0, 43000.0, 43000.0],
        )
        self.assertNotIn("CA_MB_ER_TAX", slips[0].line_ids.mapped("code"))
        line = slips[2].line_ids.filtered(lambda line: line.code == "CA_MB_ER_TAX")
        self.assertIn("Health and Post Secondary Education Tax Levy", line.name)
        self.assertRegex(line.name, r"4[.,]300")

    def test_levy_above_the_notch(self):
        """Above 5,000,000, 2.15% of the whole remuneration from the first pay."""
        self.account.employer_tax_previous_payroll = 6000000.0
        contract = self._contract(1000000.0)
        january, february = self._monthly_slips(contract, (1, 2))
        # Exemption 0: 1,000,000 x 2.15% = 21,500 on each pay.
        self._assert_lines(january, {"CA_MB_ER_TAX": 21500.0})
        self._assert_lines(february, {"CA_MB_ER_TAX": 21500.0})
        line = january.line_ids.filtered(lambda line: line.code == "CA_MB_ER_TAX")
        self.assertRegex(line.name, r"2[.,]150")

    def test_levy_associated_group(self):
        """A member of a group in the notch range takes its allocated share."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
                "employer_tax_basis": "estimate",
                "employer_tax_estimated_payroll": 3000000.0,
            }
        )
        contract = self._contract(5000.0)
        january, february, march, april = self._monthly_slips(contract, (1, 2, 3, 4))
        # Group remuneration 3,000,000: rate 4.3%. January 5,000 and
        # February 10,000 cumulative: under 12,000.
        # March: 15,000 - 12,000 = 3,000 x 4.3% = 129.00
        # April: the whole 5,000 x 4.3% = 215.00
        self._assert_lines(january, {"CA_MB_ER_TAX": 0.0, "CA_MB_SAL": 5000.0})
        self._assert_lines(february, {"CA_MB_ER_TAX": 0.0})
        self._assert_lines(march, {"CA_MB_ER_TAX": 129.0})
        self._assert_lines(april, {"CA_MB_ER_TAX": 215.0})

    # ------------------------------------------------------------------
    # WCB Manitoba
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.account.wcb_rate = 0.95
        contract = self._contract(20000.0)
        slips = self._monthly_slips(contract, range(1, 11))
        # 20,000 a month up to 171,500: August reaches 160,000, September
        # takes the 11,500 left, October nothing.
        self.assertEqual(
            [self._line(s, "CA_MB_WCB_IE") for s in slips],
            [20000.0] * 8 + [11500.0, 0.0],
        )
        # 20,000 x 0.95 / 100 = 190.00; 11,500 x 0.95 / 100 = 109.25
        self._assert_lines(slips[0], {"CA_MB_WCB": 190.0})
        self._assert_lines(slips[8], {"CA_MB_WCB": 109.25})
        self.assertNotIn("CA_MB_WCB", slips[9].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_MB_WCB")
        self.assertEqual(wcb.name, "WCB Manitoba Premium")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_MB_WCB_IE": 0.0, "CA_MB_WCB": 0.0})

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wcb_fact_sheet(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_mb_payroll.source_wcb_fact_sheet")

        def fetch(self_, url, probe=False):
            text = (
                "In 2025, the maximum level of assessable earnings is $167,050. "
                "For 2026, the maximum level of assessable earnings is $171,500."
            )
            return 200, f"<html><body><p>{text}</p></body></html>".encode()

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # 2026 matches the shipped version; 2027 is not on the page yet.
        self.assertEqual(source.watch_state, "pending")
        self.assertIn(
            "l10n_ca.mb.wcb.max_insurable = 171500.0: matches.", source.watch_message
        )

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.mb.%")]
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
