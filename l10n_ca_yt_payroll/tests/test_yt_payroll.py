# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Yukon payslips checked against the T4127 formulas (option 1) and the
step-by-step examples of the T4032 for Yukon, January 2026.

Shipped 2026 parameters used by the derivations: rates 6.4% / 9% from
58,523 (KP 1,522) / 10.9% from 117,045 (KP 3,745) / 12.8% from 181,440 (KP
7,193) / 15% from 500,000 (KP 18,193); BPAYT = BPAF, 16,452 up to a net
income of 181,440, 14,829 from 258,482, 16,452 - (NI - 181,440) x 1,623 /
77,042 in between; K4P = min(0.064 x A*, 0.064 x 1,501), A* = P x the
regular gross; WSCB maximum annual earnings 107,599 (2027: 111,580). The
federal amounts are those of the tests of l10n_ca_payroll: at 5,000 a
month, C = 280.15, EI = 81.50, F5A = 47.08, A = 12 x (5,000 - 47.08) =
59,435.04, T1 = 5,338.2924 and 444.86 of federal tax.

K1P = 0.064 x 16,452 = 1,052.928 under the phase-out. K2P = 0.064 x
(min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI, 1,123.07)), the
federal K2 items at the lowest Yukon rate. K4P = 0.064 x 1,501 = 96.064
as soon as A* reaches 1,501.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page

PREFIX = "l10n_ca.yt"

WSCB_PAGE = """<html><body><h1>Maximum annual earnings</h1>
<p>The maximum annual earnings for 2027 will be {next_year}.</p>
<p>The maximum annual earnings for past years were:</p>
<ul><li>2026 - $107,599</li><li>2025 - $104,975</li><li>2024 - $102,017</li></ul>
</body></html>"""


@tagged("post_install", "-at_install")
class TestYukonPayroll(AccountTestInvoicingCommon):
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
        cls.yukon = cls.env.ref("base.state_ca_yt")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Yukon Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Yukon Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.yukon.id,
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
        self.assertTrue({"CA_YT_SAL", "CA_YT_WCB_IE", "CA_YT_WCB"} <= codes)
        rule = self.env.ref("l10n_ca_yt_payroll.rule_yt_wcb").with_company(self.company)
        self.assertEqual(rule.account_debit.code, "512121")
        self.assertEqual(rule.account_credit.code, "221206")
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        self.assertTrue(contract.l10n_ca_prov_computed)
        self.assertEqual(contract.l10n_ca_prov_bpa, 16452.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,435.04 in [58,523, 117,045) -> V 0.09, KP 1,522
        #   K2P = 0.064 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.064 x (2,796.79 + 978) = 241.59
        #   K4P = min(0.064 x 60,000, 0.064 x 1,501) = 96.06
        #   T4 = 0.09 x 59,435.04 - 1,522 - 1,052.928 - 241.5867 - 96.064
        #      = 2,436.5749
        # (5,338.2924 + 2,436.5749) / 12 = 647.9056 -> 647.91, of which
        # 444.86 federal and 203.05 Yukon.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -203.05,
                "CA_YT_SAL": 5000.0,
                "CA_YT_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("YT", tax_line.name)
        # The company has no WSCB rate: no assessment line.
        self.assertNotIn("CA_YT_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 647.91)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Yukon, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source and
        a prescribed zone deduction of 4,015 on the TD1: A = 52 x (1,300 -
        12.33 - 80) - 4,015 = 58,783.84. The CRA gives 5,134.78 of federal
        tax and 2,345.96 of Yukon tax for the year (0.09 x 58,783.84 -
        1,522 - 0.064 x 22,227.92): 7,480.74 / 52 = 143.86, of which 98.75
        federal (5,134.78 / 52).
        """
        # 5,633.33 x 12 / 52 = 1,300.00 a week.
        contract = self._contract(
            5633.33,
            schedule_pay="weekly",
            l10n_ca_rrsp_amount=80.0,
            l10n_ca_prescribed_zone_deduction=4015.0,
        )
        slip = self._slip(contract, "2026-03-02", "2026-03-08")
        self._assert_lines(
            slip,
            {
                "BASIC": 1300.0,
                "CA_CPP": -73.35,
                "CA_EI": -21.19,
                "CA_FIT": -98.75,
                "CA_PIT": -45.11,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Yukon: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872. The CRA gives 9,406.39 federal and 4,220.37
        Yukon for the year (0.09 x 79,872 - 1,522 - 0.064 x (16,452 +
        3,519.45 + 1,123.07 + 1,501)): 13,626.76 / 52 = 262.05, of which
        180.89 federal.
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
                "CA_PIT": -81.16,
            },
        )

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1YT claim 0, other credits 120 and 20 of additional tax; K4P
        # does not depend on the claim:
        # T4 = 0.09 x 59,435.04 - 1,522 - 241.59 - 120 - 96.06 = 3,369.50
        # (5,338.29 + 3,369.50) / 12 = 725.65 -> 725.65 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -300.79})

    # ------------------------------------------------------------------
    # BPAYT and K4P
    # ------------------------------------------------------------------

    def test_bpayt_mirrors_the_federal_amount(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        vals = slip._l10n_ca_compute(contract, 5000.0)
        bpa = slip._l10n_ca_prov_bpa
        # Up to 181,440: the maximum; from 258,482: the minimum; in between
        # 16,452 - (200,000 - 181,440) x 1,623 / 77,042 = 16,061.01.
        self.assertEqual(bpa(vals, PREFIX, 181440.0), 16452.0)
        self.assertAlmostEqual(bpa(vals, PREFIX, 200000.0), 16061.01, places=2)
        self.assertEqual(bpa(vals, PREFIX, 258482.0), 14829.0)
        # NI = A + HD: with 4,015 of prescribed zone deduction, A = 200,000
        # is NI = 204,015: 16,452 - 22,575 x 1,623 / 77,042 = 15,976.43.
        contract.l10n_ca_prescribed_zone_deduction = 4015.0
        self.assertAlmostEqual(bpa(vals, PREFIX, 200000.0), 15976.43, places=2)

    def test_pay_inside_the_bpayt_phase_out(self):
        contract = self._contract(20000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        vals = slip._l10n_ca_compute(contract, 20000.0)
        # C = 0.0595 x (20,000 - 3,500 / 12) = 1,172.65, F5A = 1,172.65 x
        # 0.01 / 0.0595 = 197.08, EI = 326:
        # A = 12 x (20,000 - 197.08) = 237,635.04 in [181,440, 500,000)
        #   -> V 0.128, KP 7,193
        # BPAYT = 16,452 - (237,635.04 - 181,440) x 1,623 / 77,042
        #       = 15,268.17 -> K1P = 0.064 x 15,268.17 = 977.1629
        # K2P = 0.064 x (3,519.45 + 1,123.07) = 297.1213 (both maximums)
        # T4 = 0.128 x 237,635.04 - 7,193 - 977.1629 - 297.1213 - 96.064
        #    = 21,853.94
        self.assertAlmostEqual(vals["provincial_annual_income"], 237635.04, places=2)
        self.assertAlmostEqual(vals["provincial_annual_tax"], 21853.94, places=2)
        total = round(
            (vals["federal_annual_tax"] + vals["provincial_annual_tax"]) / 12, 2
        )
        self._assert_lines(
            slip,
            {
                "CA_FIT": -vals["federal_regular_tax"],
                "CA_PIT": -(total - vals["federal_regular_tax"]),
            },
        )

    def test_territorial_canada_employment_credit(self):
        contract = self._contract(100.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        credit = slip._l10n_ca_prov_extra_credits
        # A* = 12 x 100 = 1,200 < 1,501: K4P = 0.064 x 1,200 = 76.80.
        vals = slip._l10n_ca_compute(contract, 100.0)
        self.assertAlmostEqual(credit(vals, PREFIX, 1000.0, 0.0, 0.0), 76.80)
        # A* = 12 x 5,000: K4P = 0.064 x 1,501 = 96.064.
        vals = slip._l10n_ca_compute(contract, 5000.0)
        self.assertAlmostEqual(credit(vals, PREFIX, 59434.99, 0.0, 0.0), 96.064)
        # A* leaves out the non-periodic payments: 100 of salary and 900 of
        # bonus give A* = 1,200 again.
        vals = slip._l10n_ca_compute(contract, 1000.0, nonperiodic=900.0)
        self.assertAlmostEqual(credit(vals, PREFIX, 1000.0, 0.0, 0.0), 76.80)
        # Another prefix keeps the engine's 0.
        self.assertEqual(credit(vals, "l10n_ca.xx", 1000.0, 0.0, 0.0), 0.0)

    # ------------------------------------------------------------------
    # Workers' Safety and Compensation Board
    # ------------------------------------------------------------------

    def test_no_employer_payroll_tax(self):
        param = self.company._l10n_ca_param
        self.assertIsNone(
            param(f"{PREFIX}.employer_tax.rates", date(2026, 6, 1), default=None)
        )
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self.assertNotIn("CA_YT_ER_TAX", slip.line_ids.mapped("code"))

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.yukon.id,
                "wcb_rate": 1.67,
            }
        )
        contract = self._contract(10000.0)
        slips = self._monthly_slips(contract, range(1, 13))
        # 10,000 a month up to 107,599: October reaches 100,000, November
        # takes the 7,599 left, December nothing.
        self.assertEqual(
            [self._line(s, "CA_YT_WCB_IE") for s in slips],
            [10000.0] * 10 + [7599.0, 0.0],
        )
        # 1.67 x 10,000 / 100 = 167.00; 1.67 x 7,599 / 100 = 126.90.
        self._assert_lines(slips[0], {"CA_YT_WCB": 167.0})
        self._assert_lines(slips[10], {"CA_YT_WCB": 126.90})
        self.assertNotIn("CA_YT_WCB", slips[11].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_YT_WCB")
        self.assertEqual(wcb.name, "WSCB Assessment")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_YT_WCB_IE": 0.0, "CA_YT_WCB": 0.0})

    def test_wcb_2027_maximum(self):
        param = self.company._l10n_ca_param
        code = f"{PREFIX}.wcb.max_insurable"
        self.assertEqual(param(code, date(2026, 6, 1)), 107599)
        self.assertEqual(param(code, date(2027, 6, 1)), 111580)

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    def _watch(self, page):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_yt_payroll.source_wscb_maximum")

        def fetch(self_, url, probe=False):
            return 200, page.encode()

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        return source

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wscb_maximum(self):
        code = f"{PREFIX}.wcb.max_insurable"
        # 2026 in the list of past years and 2027 in the sentence both
        # match the shipped versions.
        source = self._watch(WSCB_PAGE.format(next_year="$111,580"))
        self.assertEqual(source.watch_state, "ok")
        self.assertIn(f"{code} = 107599.0: matches.", source.watch_message)
        self.assertIn(f"{code} = 111580.0: matches.", source.watch_message)
        # Another 2027 amount than the shipped one.
        source = self._watch(WSCB_PAGE.format(next_year="$112,000"))
        self.assertEqual(source.watch_state, "differs")
        # Before September, the page does not give the next year yet.
        page = WSCB_PAGE.replace(
            "<p>The maximum annual earnings for 2027 will be {next_year}.</p>", ""
        )
        source = self._watch(page)
        self.assertEqual(source.watch_state, "pending")
        # A page without any amount by year has changed.
        source = self._watch("<html><body><p>Maximum annual earnings</p></body></html>")
        self.assertEqual(source.watch_state, "changed")

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", f"{PREFIX}.%")]
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
