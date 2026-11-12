# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Prince Edward Island payslips checked against the T4127 formulas
(option 1) and the step-by-step examples of the T4032 for Prince Edward
Island, January and July 2026.

Shipped parameters used by the derivations: rates 9.5% / 13.47% from
33,928 (KP 1,347) / 16.6% from 65,820 (KP 3,407) / 17.62% from 106,890
(KP 4,497) / 19% from 142,520 (KP 6,464); from July 1, 2026, 21% from
200,000 (KP 10,464); from January 1, 2027, 20% from 200,000 (KP 8,464);
basic personal amount 15,000 (K1P = 0.095 x 15,000 = 1,425); WCB PEI
maximum assessable earnings 89,300. The federal amounts are those of the
tests of l10n_ca_payroll: at 5,000 a month, C = 280.15, EI = 81.50, A =
59,435.04, T1 = 5,338.29 and 444.86 of federal tax.

K2P = 0.095 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest Prince Edward Island rate.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page

PREFIX = "l10n_ca.pe"


@tagged("post_install", "-at_install")
class TestPrinceEdwardIslandPayroll(AccountTestInvoicingCommon):
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
        cls.prince_edward_island = cls.env.ref("base.state_ca_pe")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Prince Edward Island Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Prince Edward Island Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.prince_edward_island.id,
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
        self.assertTrue({"CA_PE_SAL", "CA_PE_WCB_IE", "CA_PE_WCB"} <= codes)
        self.assertNotIn("CA_PE_ER_TAX", codes)
        rule = self.env.ref("l10n_ca_pe_payroll.rule_pe_wcb").with_company(self.company)
        self.assertEqual(rule.account_debit.code, "512121")
        self.assertEqual(rule.account_credit.code, "221206")
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)

    def test_brackets_of_each_period(self):
        param = self.company._l10n_ca_param
        january = [[0, 0.095], [33928, 0.1347], [65820, 0.166], [106890, 0.1762]]
        self.assertEqual(
            param(f"{PREFIX}.brackets", date(2026, 6, 30)),
            [*january, [142520, 0.19]],
        )
        self.assertEqual(
            param(f"{PREFIX}.brackets", date(2026, 7, 1)),
            [*january, [142520, 0.19], [200000, 0.21]],
        )
        self.assertEqual(
            param(f"{PREFIX}.brackets", date(2027, 1, 1)),
            [*january, [142520, 0.19], [200000, 0.2]],
        )
        self.assertEqual(param(f"{PREFIX}.bpa", date(2026, 12, 31)), 15000)

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        self.assertTrue(contract.l10n_ca_prov_computed)
        self.assertEqual(contract.l10n_ca_prov_bpa, 15000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 12 x (5,000 - 47.08) = 59,435.04 > 33,928 -> V 0.1347, KP 1,347
        #   K2P = 0.095 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.095 x (2,796.79 + 978) = 358.61
        #   T4 = 0.1347 x 59,435.04 - 1,347 - 1,425 - 358.61 = 4,875.29
        # (5,338.29 + 4,875.29) / 12 = 851.13, of which 444.86 federal and
        # 406.27 Prince Edward Island.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -406.27,
                "CA_PE_SAL": 5000.0,
                "CA_PE_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("PE", tax_line.name)
        # The company has no WCB PEI rate: no assessment line.
        self.assertNotIn("CA_PE_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 851.13)

    def _example_below_ympe(self, date_from, date_to):
        """1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84 -> V 0.1347, KP 1,347.
        The CRA gives 5,957.85 of federal tax and 5,280.88 of Prince Edward
        Island tax for the year (provincial credits 1,831.12):
        11,238.73 / 52 = 216.13, of which 114.57 federal and 101.56 Prince
        Edward Island.
        """
        # 5,633.33 x 12 / 52 = 1,300.00 a week.
        contract = self._contract(
            5633.33, schedule_pay="weekly", l10n_ca_rrsp_amount=80.0
        )
        slip = self._slip(contract, date_from, date_to)
        self._assert_lines(
            slip,
            {
                "BASIC": 1300.0,
                "CA_CPP": -73.35,
                "CA_EI": -21.19,
                "CA_FIT": -114.57,
                "CA_PIT": -101.56,
            },
        )

    def _example_above_ympe(self, first, second):
        """1,600 a week above the YMPE: the CPP and EI maximums are reached
        and the pay bears 64 of CPP2: A = 52 x 1,536 = 79,872 -> V 0.166,
        KP 3,407. The CRA gives 9,406.39 federal and 7,985.71 Prince Edward
        Island for the year (provincial credits 1,866.04): 17,392.10 / 52 =
        334.46, of which 180.89 federal and 153.57 Prince Edward Island.
        """
        # 6,933.33 x 12 / 52 = 1,600.00 a week.
        contract = self._contract(6933.33, schedule_pay="weekly")
        # A first pay of 76,000 reaches both maximums and bears 56 of CPP2.
        self._slip(contract, *first, done=True, bonus=74400.0)
        slip = self._slip(contract, *second)
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": -64.0,
                "CA_EI": 0.0,
                "CA_FIT": -180.89,
                "CA_PIT": -153.57,
            },
        )

    def test_t4032_example_below_ympe(self):
        """First example of the T4032 for Prince Edward Island, January 2026."""
        self._example_below_ympe("2026-03-02", "2026-03-08")

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Prince Edward Island, January 2026."""
        self._example_above_ympe(
            ("2026-01-05", "2026-01-11"), ("2026-01-12", "2026-01-18")
        )

    def test_t4032_examples_july(self):
        """The examples of the T4032 for Prince Edward Island, July 2026.

        Same totals as in January (216.13 and 334.46 a week): A stays below
        200,000, where the brackets of July 1, 2026 are those of January.
        """
        self._example_below_ympe("2026-07-06", "2026-07-12")
        self._example_above_ympe(
            ("2026-07-06", "2026-07-12"), ("2026-07-13", "2026-07-19")
        )

    def test_prorated_bracket_above_200000(self):
        """20,000 a month: the pay of June withholds 19% above 142,520, the
        pay of July the prorated 21% above 200,000.

        C = 0.0595 x (20,000 - 291.66) = 1,172.65; EI = 0.0163 x 20,000 =
        326.00; F5 = 1,172.65 x 0.01 / 0.0595 = 197.08 (rounded to the cent);
        A = 12 x (20,000 - 197.08) = 237,635.04.
        Federal: R 0.29, K 15,685; BPAF = 16,452 - (237,635.04 - 181,440) x
        1,623 / 77,042 = 15,268.17, K1 = 2,137.54; K2 = 0.14 x (3,519.45 +
        1,123.07) = 649.95 (P x C x 0.0495 / 0.0595 = 11,706.79 and P x EI
        = 3,912 exceed both maximums); K4 = 0.14 x 1,501 = 210.14.
        T1 = 0.29 x 237,635.04 - 15,685 - 2,137.54 - 649.95 - 210.14 =
        50,231.52 -> 4,185.96 federal.
        K2P = 0.095 x (3,519.45 + 1,123.07) = 441.04.
        June: T4 = 0.19 x 237,635.04 - 6,464 - 1,425 - 441.04 = 36,820.62;
        (50,231.52 + 36,820.62) / 12 = 7,254.35 -> 3,068.39.
        July: T4 = 0.21 x 237,635.04 - 10,464 - 1,425 - 441.04 = 37,573.32;
        (50,231.52 + 37,573.32) / 12 = 7,317.07 -> 3,131.11.
        The prorated bracket adds 0.02 x (237,635.04 - 200,000) = 752.70 to
        the tax of the year.
        """
        contract = self._contract(20000.0)
        june = self._slip(contract, "2026-06-01", "2026-06-30")
        july = self._slip(contract, "2026-07-01", "2026-07-31")
        for slip, tax in ((june, 3068.39), (july, 3131.11)):
            self._assert_lines(
                slip,
                {
                    "CA_CPP": -1172.65,
                    "CA_EI": -326.0,
                    "CA_FIT": -4185.96,
                    "CA_PIT": -tax,
                },
            )
        vals = {}
        for slip in (june, july):
            vals[slip] = slip._l10n_ca_compute(contract, 20000.0)
            self.assertAlmostEqual(
                vals[slip]["provincial_annual_income"], 237635.04, places=2
            )
        self.assertAlmostEqual(vals[june]["provincial_annual_tax"], 36820.62, places=2)
        self.assertAlmostEqual(vals[july]["provincial_annual_tax"], 37573.32, places=2)
        self.assertAlmostEqual(
            vals[july]["provincial_annual_tax"] - vals[june]["provincial_annual_tax"],
            752.70,
            places=2,
        )

    def test_annual_rate_of_2027(self):
        """From 2027 the rate above 200,000 is the annual 20% (KP 8,464).

        Same A and K2P as above: T4 = 0.20 x 237,635.04 - 8,464 - 1,425 -
        441.04 = 37,196.97; the prorated 21% applies up to December 31,
        2026.
        """
        contract = self._contract(20000.0)
        slip = self.env["hr.payslip"]
        for day, tax in (
            (date(2026, 6, 30), 36820.62),
            (date(2026, 12, 31), 37573.32),
            (date(2027, 1, 1), 37196.97),
        ):
            vals = {"company": self.company, "contract": contract, "date": day}
            result = slip._l10n_ca_prov_annual_tax(vals, PREFIX, 237635.04, 441.0394)
            self.assertAlmostEqual(result["tax"], tax, places=2, msg=str(day))
            self.assertFalse(result["surtax"] or result["reduction"] or result["lcp"])

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1PE claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.1347 x 59,435.04 - 1,347 - 358.61 - 120 = 6,180.29
        # (5,338.29 + 6,180.29) / 12 = 959.88 -> 959.88 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -535.02})

    # ------------------------------------------------------------------
    # Employer contributions
    # ------------------------------------------------------------------

    def test_no_employer_payroll_tax(self):
        param = self.company._l10n_ca_param
        self.assertIsNone(
            param(f"{PREFIX}.employer_tax.rates", date(2026, 3, 1), default=None)
        )
        contract = self._contract(20000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        vals = slip._l10n_ca_compute(contract, 20000.0)
        self.assertEqual(vals["employer_tax"], 0.0)
        self.assertEqual(vals["province_remuneration"], 20000.0)

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.prince_edward_island.id,
                "wcb_rate": 1.28,
            }
        )
        contract = self._contract(10000.0)
        slips = self._monthly_slips(contract, range(1, 11))
        # 10,000 a month up to 89,300: August reaches 80,000, September
        # takes the 9,300 left, October nothing.
        self.assertEqual(
            [self._line(s, "CA_PE_WCB_IE") for s in slips],
            [10000.0] * 8 + [9300.0, 0.0],
        )
        # 1.28 x 10,000 / 100 = 128.00; 1.28 x 9,300 / 100 = 119.04
        self._assert_lines(slips[0], {"CA_PE_WCB": 128.0})
        self._assert_lines(slips[8], {"CA_PE_WCB": 119.04})
        self.assertNotIn("CA_PE_WCB", slips[9].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_PE_WCB")
        self.assertEqual(wcb.name, "WCB PEI Assessment")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_PE_WCB_IE": 0.0, "CA_PE_WCB": 0.0})

    def test_wcb_maximum_of_2026_only(self):
        # The 2027 maximum is not published: a 2027 pay still reads the
        # version of 2026.
        version = self.company._l10n_ca_param_version(
            f"{PREFIX}.wcb.max_insurable", date(2027, 6, 1)
        )
        self.assertEqual(version.date_from, date(2026, 1, 1))
        self.assertEqual(version.parameter_id.version_ids, version)
        self.assertEqual(
            self.company._l10n_ca_param(
                f"{PREFIX}.wcb.max_insurable", date(2026, 6, 1)
            ),
            89300,
        )

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wcb_pei_rates_page(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_pe_payroll.source_wcb_rates_payments")

        def fetch(self_, url, probe=False):
            text = (
                "They're calculated per $100 of assessable payroll based on the "
                "maximum assessable earnings (MAE) for that year. The MAE for "
                "2026 is $89,300."
            )
            return 200, f"<html><body><p>{text}</p></body></html>".encode()

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # 2026 matches the shipped version; 2027 is not on the page yet.
        self.assertEqual(source.watch_state, "pending")
        self.assertIn(
            "l10n_ca.pe.wcb.max_insurable = 89300.0: matches.", source.watch_message
        )

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.pe.%")]
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
