# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""New Brunswick payslips checked against the T4127 formulas (option 1)
and the step-by-step examples of the T4032 for New Brunswick, January 2026.

Shipped 2026 parameters used by the derivations: rates 9.4% / 14% from
52,333 (KP 2,407) / 16% from 104,666 (KP 4,501) / 19.5% from 193,861 (KP
11,286); basic personal amount 13,664 (K1P = 0.094 x 13,664 = 1,284.42);
LCP 20% of the shares withheld, at most 2,000; WorkSafeNB maximum
assessable earnings 85,800 (2027: 88,200). The federal amounts are those
of the tests of l10n_ca_payroll: at 5,000 a month, C = 280.15, EI = 81.50,
A = 59,435.04, T1 = 5,338.29 and 444.86 of federal tax.

K2P = 0.094 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest New Brunswick rate.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page


@tagged("post_install", "-at_install")
class TestNewBrunswickPayroll(AccountTestInvoicingCommon):
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
        cls.new_brunswick = cls.env.ref("base.state_ca_nb")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "New Brunswick Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "New Brunswick Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.new_brunswick.id,
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
        self.assertTrue({"CA_NB_SAL", "CA_NB_WCB_IE", "CA_NB_WCB"} <= codes)
        rule = self.env.ref("l10n_ca_nb_payroll.rule_nb_wcb").with_company(self.company)
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
        self.assertEqual(contract.l10n_ca_prov_bpa, 13664.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,435.04 > 52,333 -> V 0.14, KP 2,407
        #   K2P = 0.094 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.094 x (2,796.79 + 978) = 354.83
        #   T4 = 0.14 x 59,435.04 - 2,407 - 1,284.42 - 354.83 = 4,274.66
        # (5,338.29 + 4,274.66) / 12 = 801.08, of which 444.86 federal and
        # 356.22 New Brunswick.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -356.22,
                "CA_NB_SAL": 5000.0,
                "CA_NB_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("NB", tax_line.name)
        # The company has no WorkSafeNB rate: no assessment line.
        self.assertNotIn("CA_NB_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 801.08)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for New Brunswick, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84. The CRA gives 5,957.85
        of federal tax and 4,698.58 of New Brunswick tax for the year:
        10,656.43 / 52 = 204.93, of which 114.57 federal.
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
                "CA_PIT": -90.36,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for New Brunswick: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872. The CRA gives 9,406.39 federal and 7,054.27
        New Brunswick for the year: 16,460.66 / 52 = 316.55, of which
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
                "CA_PIT": -135.66,
            },
        )

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1NB claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.14 x 59,435.04 - 2,407 - 354.83 - 120 = 5,439.08
        # (5,338.29 + 5,439.08) / 12 = 898.11 -> 898.11 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -473.25})

    def test_labour_sponsored_funds_credit(self):
        # 100 of shares a month: LCP = min(2,000, 20% x 100) = 20 a pay,
        # P x LCP = 240 for the year: T2 = 4,274.66 - 240 = 4,034.66 and
        # (5,338.29 + 4,034.66) / 12 = 781.08 -> 336.22 New Brunswick.
        contract = self._contract(5000.0, l10n_ca_lsvcc_amount=100.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(
            slip,
            {
                "CA_LSVCC": -100.0,
                "CA_FIT": -444.86,
                "CA_PIT": -336.22,
                "NET": 5000.0 - 100.0 - 280.15 - 81.50 - 444.86 - 336.22,
            },
        )
        # 2,000 a month reaches the maximum of the year: 12 x 400 > 2,000.
        contract.l10n_ca_lsvcc_amount = 2000.0
        vals = slip._l10n_ca_compute(contract, 5000.0)
        self.assertAlmostEqual(vals["provincial_lcp"], 2000.0)

    # ------------------------------------------------------------------
    # WorkSafeNB
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.new_brunswick.id,
                "wcb_rate": 1.10,
            }
        )
        contract = self._contract(10000.0)
        slips = self._monthly_slips(contract, range(1, 11))
        # 10,000 a month up to 85,800: August reaches 80,000, September
        # takes the 5,800 left, October nothing.
        self.assertEqual(
            [self._line(s, "CA_NB_WCB_IE") for s in slips],
            [10000.0] * 8 + [5800.0, 0.0],
        )
        self._assert_lines(slips[0], {"CA_NB_WCB": 110.0})
        self._assert_lines(slips[8], {"CA_NB_WCB": 63.80})
        self.assertNotIn("CA_NB_WCB", slips[9].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_NB_WCB")
        self.assertEqual(wcb.name, "WorkSafeNB Assessment")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_NB_WCB_IE": 0.0, "CA_NB_WCB": 0.0})

    def test_wcb_2027_maximum(self):
        param = self.company._l10n_ca_param
        self.assertEqual(param("l10n_ca.nb.wcb.max_insurable", date(2026, 6, 1)), 85800)
        self.assertEqual(param("l10n_ca.nb.wcb.max_insurable", date(2027, 6, 1)), 88200)

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    @freeze_time("2026-11-15")
    def test_watcher_of_the_worksafenb_policy(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_nb_payroll.source_worksafenb_policy_37_110")

        def fetch(self_, url, probe=False):
            text = (
                "The 2026 yearly maximum assessable earnings is eighty-five "
                "thousand eight hundred dollars ($85,800) per worker."
            )
            return 200, f"<html><body><p>{text}</p></body></html>".encode()

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # 2026 matches the shipped version; 2027 is not on the page yet.
        self.assertEqual(source.watch_state, "pending")
        self.assertIn(
            "l10n_ca.nb.wcb.max_insurable = 85800.0: matches.", source.watch_message
        )

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.nb.%")]
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
