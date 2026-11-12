# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Nunavut payslips checked against the T4127 formulas (option 1) and the
step-by-step examples of the T4032 for Nunavut, January 2026.

Shipped 2026 parameters used by the derivations: rates 4% / 7% from 55,801
(KP 1,674) / 9% from 111,602 (KP 3,906) / 11.5% from 181,439 (KP 8,442);
basic personal amount 19,659 (K1P = 0.04 x 19,659 = 786.36); payroll tax
2% of the gross; WSCC maximum insurable remuneration 117,300. The federal
amounts are those of the tests of l10n_ca_payroll: at 5,000 a month, C =
280.15, EI = 81.50, F5A = 47.08, A = 59,435.04, T1 = 5,338.29 and 444.86
of federal tax.

K2P = 0.04 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest territorial rate.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page


@tagged("post_install", "-at_install")
class TestNunavutPayroll(AccountTestInvoicingCommon):
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
        cls.territory = cls.env.ref("base.state_ca_nu")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Nunavut Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Nunavut Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.territory.id,
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
            {"CA_NU_SAL", "CA_NU_WCB_IE", "CA_NU_PAYROLL_TAX", "CA_NU_WCB"} <= codes
        )
        accounts = {
            "rule_nu_payroll_tax": ("221206", "221203"),
            "rule_nu_wcb": ("512121", "221206"),
        }
        for xmlid, (debit, credit) in accounts.items():
            rule = self.env.ref(f"l10n_ca_nu_payroll.{xmlid}").with_company(
                self.company
            )
            self.assertEqual(rule.account_debit.code, debit, xmlid)
            self.assertEqual(rule.account_credit.code, credit, xmlid)
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        self.assertTrue(contract.l10n_ca_prov_computed)
        self.assertEqual(contract.l10n_ca_prov_bpa, 19659.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # F5A = 47.08, rounded to the cent like the examples of the CRA:
        # A = 12 x (5,000 - 47.08) = 59,435.04 > 55,801 -> V 0.07, KP 1,674
        #   T1 = 0.205 x 59,435.04 - 3,804 - 2,303.28 - 528.47 - 210.14
        #      = 5,338.29
        #   K2P = 0.04 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.04 x (2,796.78 + 978) = 150.99
        #   T4 = 0.07 x 59,435.04 - 1,674 - 786.36 - 150.99 = 1,549.10
        # (5,338.29 + 1,549.10) / 12 = 573.95, of which 444.86 federal and
        # 129.09 Nunavut.
        # Payroll tax 2% x 5,000 = 100.00: it does not lower A.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -129.09,
                "CA_NU_PAYROLL_TAX": -100.0,
                "CA_NU_SAL": 5000.0,
                "CA_NU_WCB_IE": 5000.0,
                "NET": 5000.0 - 280.15 - 81.50 - 444.86 - 129.09 - 100.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("NU", tax_line.name)
        # The company has no WSCC rate: no assessment line.
        self.assertNotIn("CA_NU_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 573.95)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Nunavut, January 2026:
        1,300 a week with an RRSP contribution of 80 withheld at source and
        an annual deduction for living in a prescribed zone of 4,015 (HD).

        A = 52 x (1,300 - 12.33 - 80) - 4,015 = 58,783.84
        -> V 0.07, KP 1,674;
        T4 = 0.07 x 58,783.84 - 1,674 - 786.36
             - 0.04 x (3,173.04 + 1,101.88) = 1,483.51.
        The CRA gives 5,134.78 federal and 1,483.51 territorial for the year:
        6,618.29 / 52 = 127.27, of which 98.75 federal and 28.52 Nunavut.
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
                "CA_PIT": -28.52,
                "CA_NU_PAYROLL_TAX": -26.0,
            },
        )
        self.assertAlmostEqual(
            self._line(slip, "CA_FIT") + self._line(slip, "CA_PIT"), -127.27
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Nunavut: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872 -> V 0.07, KP 1,674;
        T4 = 0.07 x 79,872 - 1,674 - 0.04 x (19,659 + 3,519.45 +
        1,123.07) = 2,944.98. The CRA gives 9,406.39 federal and 2,944.98
        territorial for the year: 12,351.37 / 52 = 237.53, of which 180.89
        federal and 56.64 Nunavut.
        """
        # 6,933.33 x 12 / 52 = 1,600.00 a week.
        contract = self._contract(6933.33, schedule_pay="weekly")
        # A first pay of 76,000 reaches both maximums and bears 56 of CPP2;
        # its payroll tax is 2% x 76,000 = 1,520.
        first = self._slip(
            contract, "2026-01-05", "2026-01-11", done=True, bonus=74400.0
        )
        self._assert_lines(first, {"CA_NU_PAYROLL_TAX": -1520.0})
        slip = self._slip(contract, "2026-01-12", "2026-01-18")
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": -64.0,
                "CA_EI": 0.0,
                "CA_FIT": -180.89,
                "CA_PIT": -56.64,
                "CA_NU_PAYROLL_TAX": -32.0,
            },
        )
        self.assertAlmostEqual(
            self._line(slip, "CA_FIT") + self._line(slip, "CA_PIT"), -237.53
        )

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1NU claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.07 x 59,435.04 - 1,674 - 150.99 - 120 = 2,215.46
        # (5,338.29 + 2,215.46) / 12 = 629.48 -> 629.48 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -204.62})

    # ------------------------------------------------------------------
    # Payroll tax
    # ------------------------------------------------------------------

    def test_payroll_tax(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        line = slip.line_ids.filtered(lambda line: line.code == "CA_NU_PAYROLL_TAX")
        self.assertEqual(line.name, "Nunavut Payroll Tax")
        self.assertEqual(
            line.salary_rule_id.register_id.partner_id,
            self.env.ref("l10n_ca_nu_payroll.partner_gn"),
        )
        self.assertEqual(
            slip._l10n_ca_compute(contract, 5000.0)["nu_payroll_tax"], 100.0
        )
        # 2% x 4,321.27 = 86.4254 -> 86.43
        vals = slip._l10n_ca_compute(contract, 4321.27)
        self.assertEqual(vals["nu_payroll_tax"], 86.43)
        self.assertEqual(vals["nu_payroll_tax_rate"], 0.02)
        # An exempt contract has no payroll tax line; the income tax stays.
        exempt = self._contract(5000.0, l10n_ca_nu_payroll_tax_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self.assertNotIn("CA_NU_PAYROLL_TAX", slip.line_ids.mapped("code"))
        self._assert_lines(
            slip,
            {"CA_PIT": -129.09, "NET": 5000.0 - 280.15 - 81.50 - 444.86 - 129.09},
        )

    def test_payroll_tax_credit_note(self):
        """A credit note takes the payroll tax of the pay back."""
        contract = self._contract(5000.0)
        march = self._monthly_slips(contract, (3,))[0]
        self._assert_lines(march, {"CA_NU_PAYROLL_TAX": -100.0})
        march.refund_sheet()
        refund = march.refunded_id
        self.assertTrue(refund.credit_note)
        self.assertEqual(refund.state, "done")
        # The credit note bears the line of the pay; its lines count
        # negatively, so the payroll tax withheld in the year is back to 0.
        self._assert_lines(refund, {"CA_NU_PAYROLL_TAX": -100.0})
        domain = [("employee_id", "=", contract.employee_id.id), ("state", "=", "done")]
        self.assertAlmostEqual(
            march._l10n_ca_line_total(domain, "CA_NU_PAYROLL_TAX"), 0.0
        )
        self.assertAlmostEqual(march._l10n_ca_line_total(domain, "CA_NU_SAL"), 0.0)
        # A credit note computed as such gives the same amounts.
        computed = self.env["hr.payslip"].create(
            {
                "employee_id": contract.employee_id.id,
                "contract_id": contract.id,
                "struct_id": self.structure.id,
                "company_id": self.company.id,
                "date_from": "2026-03-01",
                "date_to": "2026-03-28",
                "credit_note": True,
            }
        )
        computed.compute_sheet()
        self._assert_lines(computed, {"CA_NU_PAYROLL_TAX": -100.0})

    # ------------------------------------------------------------------
    # WSCC
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.territory.id,
                "wcb_rate": 2.40,
            }
        )
        contract = self._contract(12000.0)
        slips = self._monthly_slips(contract, range(1, 12))
        # 12,000 a month up to 117,300: September reaches 108,000, October
        # takes the 9,300 left, November nothing.
        self.assertEqual(
            [self._line(s, "CA_NU_WCB_IE") for s in slips],
            [12000.0] * 9 + [9300.0, 0.0],
        )
        # 2.40 x 12,000 / 100 = 288.00; 2.40 x 9,300 / 100 = 223.20
        self._assert_lines(slips[0], {"CA_NU_WCB": 288.0})
        self._assert_lines(slips[9], {"CA_NU_WCB": 223.2})
        self.assertNotIn("CA_NU_WCB", slips[10].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_NU_WCB")
        self.assertEqual(wcb.name, "WSCC Assessment (Nunavut)")
        # A contract not covered has no assessable payroll.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_NU_WCB_IE": 0.0, "CA_NU_WCB": 0.0})

    def test_wcb_maximum(self):
        param = self.company._l10n_ca_param
        self.assertEqual(
            param("l10n_ca.nu.wcb.max_insurable", date(2026, 6, 1)), 117300
        )

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wscc_rates(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_nu_payroll.source_wscc_rates")

        def fetch(self_, url, probe=False):
            rows = (
                ("2026", "NWT: $116,000 &nbsp;- &nbsp;NU: $117,300&nbsp;"),
                ("2025", "NWT: $112,600 &nbsp;- &nbsp;NU: $113,900&nbsp;"),
                ("2024", "$110,600"),
            )
            table = "".join(f"<tr><td>{y}</td><td>{v}</td></tr>" for y, v in rows)
            return 200, f"<html><body><table>{table}</table></body></html>".encode()

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # 2026 matches the shipped version; 2027 is not on the page yet.
        self.assertEqual(source.watch_state, "pending")
        self.assertIn(
            "l10n_ca.nu.wcb.max_insurable = 117300.0: matches.", source.watch_message
        )

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.nu.%")]
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
