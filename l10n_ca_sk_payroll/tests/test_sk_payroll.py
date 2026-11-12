# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Saskatchewan payslips checked against the T4127 formulas (option 1)
and the step-by-step examples of the T4032 for Saskatchewan, January 2026.

Shipped 2026 parameters used by the derivations: rates 10.5% / 12.5% from
54,532 (KP 1,091) / 14.5% from 155,805 (KP 4,207); basic personal amount
20,381 (K1P = 0.105 x 20,381 = 2,140.005); LCP 17.5% of the shares
withheld, at most 875; Saskatchewan WCB maximum assessable earnings
108,223. The federal amounts are those of the tests of l10n_ca_payroll: at
5,000 a month, C = 280.15, EI = 81.50, A = 59,435.04, T1 = 5,338.29 and
444.86 of federal tax.

K2P = 0.105 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest Saskatchewan rate.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page

from ..watch import wcbsask_maximum

# Table of the WCB page as it is laid out: the years, then their maximums.
WCB_PAGE = (
    "<html><body><p>The maximum assessable wage rate for 2026 is $108,223.</p>"
    "<table><tbody><tr><td><strong>2023</strong></td><td><strong>2024</strong>"
    "</td><td><strong>2025</strong></td><td><strong>2026</strong></td></tr>"
    "<tr><td>$96,945</td><td>$99,945</td><td>$104,531</td><td>$108,223</td></tr>"
    "</tbody></table></body></html>"
)


@tagged("post_install", "-at_install")
class TestSaskatchewanPayroll(AccountTestInvoicingCommon):
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
        cls.saskatchewan = cls.env.ref("base.state_ca_sk")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Saskatchewan Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Saskatchewan Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.saskatchewan.id,
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
        self.assertTrue({"CA_SK_SAL", "CA_SK_WCB_IE", "CA_SK_WCB"} <= codes)
        # Saskatchewan has no employer payroll tax.
        self.assertNotIn("CA_SK_ER_TAX", codes)
        rule = self.env.ref("l10n_ca_sk_payroll.rule_sk_wcb").with_company(self.company)
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
        self.assertEqual(contract.l10n_ca_prov_bpa, 20381.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,435.04 > 54,532 -> V 0.125, KP 1,091
        #   K2P = 0.105 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.105 x (2,796.79 + 978) = 396.35
        #   T4 = 0.125 x 59,435.04 - 1,091 - 2,140.005 - 396.35 = 3,802.02
        # (5,338.29 + 3,802.02) / 12 = 761.69, of which 444.86 federal and
        # 316.83 Saskatchewan.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -316.83,
                "CA_SK_SAL": 5000.0,
                "CA_SK_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("SK", tax_line.name)
        # The company has no WCB rate: no premium line, and no employer tax.
        self.assertNotIn("CA_SK_WCB", slip.line_ids.mapped("code"))
        vals = slip._l10n_ca_compute(contract, 5000.0)
        self.assertEqual(vals["employer_tax"], 0.0)
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 761.69)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Saskatchewan, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84. The CRA gives 5,957.85
        of federal tax and 4,169.99 of Saskatchewan tax for the year
        (0.125 x 62,798.84 - 1,091 - 2,588.87 of credits at 10.5%):
        10,127.84 / 52 = 194.77, of which 114.57 federal and 80.20
        Saskatchewan.
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
                "CA_PIT": -80.20,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Saskatchewan: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872. The CRA gives 9,406.39 federal and 6,265.53
        Saskatchewan for the year (0.125 x 79,872 - 1,091 - 2,627.47 of
        credits at 10.5%): 15,671.92 / 52 = 301.38, of which 180.89 federal
        and 120.49 Saskatchewan.
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
                "CA_PIT": -120.49,
            },
        )

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1SK claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.125 x 59,435.04 - 1,091 - 396.35 - 120 = 5,822.03
        # (5,338.29 + 5,822.03) / 12 = 930.03 -> 930.03 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -505.17})

    def test_labour_sponsored_funds_credit(self):
        # 100 of shares a month: LCP = min(875, 17.5% x 100) = 17.50 a pay,
        # P x LCP = 210 for the year: T2 = 3,802.02 - 210 = 3,592.02 and
        # (5,338.29 + 3,592.02) / 12 = 744.19 -> 299.33 Saskatchewan.
        contract = self._contract(5000.0, l10n_ca_lsvcc_amount=100.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(
            slip,
            {
                "CA_LSVCC": -100.0,
                "CA_FIT": -444.86,
                "CA_PIT": -299.33,
                "NET": 5000.0 - 100.0 - 280.15 - 81.50 - 444.86 - 299.33,
            },
        )
        # 500 a month reaches the maximum of the year: 12 x 87.50 = 1,050
        # > 875.
        contract.l10n_ca_lsvcc_amount = 500.0
        vals = slip._l10n_ca_compute(contract, 5000.0)
        self.assertAlmostEqual(vals["provincial_lcp"], 875.0)

    def test_no_july_2026_change(self):
        # T4127 123rd edition: no Saskatchewan change on July 1, 2026.
        param = self.company._l10n_ca_param
        for code in ("brackets", "bpa", "lcp_rate", "lcp_max"):
            self.assertEqual(
                param(f"l10n_ca.sk.{code}", date(2026, 7, 1)),
                param(f"l10n_ca.sk.{code}", date(2026, 1, 1)),
                code,
            )
        self.assertEqual(param("l10n_ca.sk.bpa", date(2026, 7, 1)), 20381)

    def test_2027_pay_warns_of_the_2026_amounts(self):
        # The 2027 basic personal amount is not published: a 2027 pay uses
        # the 2026 amounts and says so.
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2027-01-01", "2027-01-31")
        self.assertIn(
            "The indexed amounts of 2027 are not entered (time parameter "
            "l10n_ca.sk.bpa): this payslip uses those of 2026.",
            slip.l10n_ca_warning,
        )

    # ------------------------------------------------------------------
    # Saskatchewan WCB
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.saskatchewan.id,
                "wcb_rate": 1.22,
            }
        )
        contract = self._contract(13000.0)
        slips = self._monthly_slips(contract, range(1, 11))
        # 13,000 a month up to 108,223: August reaches 104,000, September
        # takes the 4,223 left, October nothing.
        self.assertEqual(
            [self._line(s, "CA_SK_WCB_IE") for s in slips],
            [13000.0] * 8 + [4223.0, 0.0],
        )
        # 13,000 x 1.22 / 100 = 158.60; 4,223 x 1.22 / 100 = 51.52.
        self._assert_lines(slips[0], {"CA_SK_WCB": 158.60})
        self._assert_lines(slips[8], {"CA_SK_WCB": 51.52})
        self.assertNotIn("CA_SK_WCB", slips[9].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_SK_WCB")
        self.assertEqual(wcb.name, "Saskatchewan WCB Premium")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(13000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_SK_WCB_IE": 0.0, "CA_SK_WCB": 0.0})

    def test_wcb_maximum_by_year(self):
        param = self.company._l10n_ca_param
        self.assertEqual(
            param("l10n_ca.sk.wcb.max_insurable", date(2026, 6, 1)), 108223
        )
        # The 2027 maximum is not published: no 2027 version is shipped.
        versions = self.env.ref(
            "l10n_ca_sk_payroll.param_sk_wcb_max_insurable"
        ).version_ids
        self.assertEqual(versions.mapped("date_from"), [date(2026, 1, 1)])

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    def test_watcher_reads_the_table(self):
        self.assertEqual(
            wcbsask_maximum(WCB_PAGE.encode(), 2025),
            {"l10n_ca.sk.wcb.max_insurable": 104531.0},
        )
        self.assertIsNone(wcbsask_maximum(WCB_PAGE.encode(), 2027))

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wcb_page(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_sk_payroll.source_wcbsask_maximum")

        def fetch(self_, url, probe=False):
            return 200, WCB_PAGE.encode()

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # 2026 matches the shipped version; 2027 is not on the page yet.
        self.assertEqual(source.watch_state, "pending")
        self.assertIn(
            "l10n_ca.sk.wcb.max_insurable = 108223.0: matches.", source.watch_message
        )

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.sk.%")]
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
