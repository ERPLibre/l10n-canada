# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Nova Scotia payslips checked against the T4127 formulas (option 1)
and the step-by-step examples of the T4032 for Nova Scotia, January 2026.

Shipped 2026 parameters used by the derivations: rates 8.79% / 14.95% from
30,995 (KP 1,909) / 16.67% from 61,991 (KP 2,976) / 17.5% from 97,417 (KP
3,784) / 21% from 157,124 (KP 9,283); basic personal amount 11,932 for
every income (K1P = 0.0879 x 11,932 = 1,048.82); LCP 20% of the shares
withheld, at most 2,000; WCB Nova Scotia maximum assessable earnings 79,900
(2027: 83,300). The federal amounts are those of the tests of
l10n_ca_payroll: at 5,000 a month, C = 280.15, EI = 81.50, A = 59,435.04,
T1 = 5,338.29 and 444.86 of federal tax.

K2P = 0.0879 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest Nova Scotia rate.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page

# Page of the WCB Nova Scotia maximum assessable earnings once the next
# year is published: the sentence names that year, the table the others.
WCB_PAGE = """<html><body>
<h2>Maximum for {latest}</h2>
<p>The maximum assessable earnings for {latest} is ${amount}.</p>
<h2>Maximums for previous years</h2>
<table>
<tr><th>Year</th><th>Maximum Assessable Earnings</th></tr>
{rows}
</table>
</body></html>"""


def wcb_page(latest, amount, previous):
    rows = "".join(f"<tr><td>{y}</td><td>${a}</td></tr>" for y, a in previous)
    return WCB_PAGE.format(latest=latest, amount=amount, rows=rows).encode()


@tagged("post_install", "-at_install")
class TestNovaScotiaPayroll(AccountTestInvoicingCommon):
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
        cls.nova_scotia = cls.env.ref("base.state_ca_ns")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Nova Scotia Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Nova Scotia Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.nova_scotia.id,
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
        self.assertTrue({"CA_NS_SAL", "CA_NS_WCB_IE", "CA_NS_WCB"} <= codes)
        rule = self.env.ref("l10n_ca_ns_payroll.rule_ns_wcb").with_company(self.company)
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
        self.assertEqual(contract.l10n_ca_prov_bpa, 11932.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,435.04, from 30,995 to 61,991 -> V 0.1495, KP 1,909
        #   K2P = 0.0879 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.0879 x (2,796.79 + 978) = 331.80
        #   T4 = 0.1495 x 59,435.04 - 1,909 - 1,048.82 - 331.80
        #      = 8,885.54 - 3,289.62 = 5,595.92
        # (5,338.29 + 5,595.92) / 12 = 911.18, of which 444.86 federal and
        # 466.32 Nova Scotia.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -466.32,
                "CA_NS_SAL": 5000.0,
                "CA_NS_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("NS", tax_line.name)
        # The company has no WCB Nova Scotia rate: no premium line.
        self.assertNotIn("CA_NS_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 911.18)

    def test_basic_personal_amount_flat(self):
        """The basic personal amount does not fall with the income.

        T4127 removes the BPANS formula for 2026: the employer uses 11,932
        for every employee. At 20,000 a month, A is far above the former
        reduction threshold and the claim stays 11,932.
        """
        low = self._contract(1500.0)
        high = self._contract(20000.0)
        slip = self._slip(high, "2026-03-01", "2026-03-31")
        for contract in (low, high):
            vals = slip._l10n_ca_compute(contract, contract.wage)
            if contract == high:
                self.assertGreater(vals["federal_annual_income"], 200000.0)
            self.assertAlmostEqual(
                slip._l10n_ca_prov_claim(
                    vals, "l10n_ca.ns", vals["federal_annual_income"]
                ),
                11932.0,
            )

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Nova Scotia, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84, V 0.1667, KP 2,976. The
        CRA gives 5,957.85 of federal tax and 6,067.98 of Nova Scotia tax
        for the year (10,468.57 - 2,976 - 1,424.59 of credits K1P + K2P):
        12,025.83 / 52 = 231.27, of which 114.57 federal and 116.70 Nova
        Scotia.
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
                "CA_PIT": -116.70,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Nova Scotia: 1,600 a week.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872, V 0.1667, KP 2,976. The CRA gives 9,406.39
        federal and 8,881.76 Nova Scotia for the year (13,314.66 - 2,976 -
        1,456.90 of credits K1P + K2P): 18,288.15 / 52 = 351.70, of which
        180.89 federal and 170.81 Nova Scotia.
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
                "CA_PIT": -170.81,
            },
        )

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1NS claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.1495 x 59,435.04 - 1,909 - 331.80 - 120 = 6,524.74
        # (5,338.29 + 6,524.74) / 12 = 988.59 -> 988.59 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -563.73})

    def test_labour_sponsored_funds_credit(self):
        # 100 of shares a month: LCP = min(2,000, 20% x 100) = 20 a pay,
        # P x LCP = 240 for the year: T2 = 5,595.92 - 240 = 5,355.92 and
        # (5,338.29 + 5,355.92) / 12 = 891.18 -> 446.32 Nova Scotia.
        contract = self._contract(5000.0, l10n_ca_lsvcc_amount=100.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(
            slip,
            {
                "CA_LSVCC": -100.0,
                "CA_FIT": -444.86,
                "CA_PIT": -446.32,
                "NET": 5000.0 - 100.0 - 280.15 - 81.50 - 444.86 - 446.32,
            },
        )
        # 2,000 a month reaches the maximum of the year: 12 x 400 > 2,000.
        contract.l10n_ca_lsvcc_amount = 2000.0
        vals = slip._l10n_ca_compute(contract, 5000.0)
        self.assertAlmostEqual(vals["provincial_lcp"], 2000.0)

    # ------------------------------------------------------------------
    # WCB Nova Scotia
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.nova_scotia.id,
                "wcb_rate": 2.65,
            }
        )
        contract = self._contract(10000.0)
        slips = self._monthly_slips(contract, range(1, 10))
        # 10,000 a month up to 79,900: July reaches 70,000, August takes
        # the 9,900 left, September nothing.
        self.assertEqual(
            [self._line(s, "CA_NS_WCB_IE") for s in slips],
            [10000.0] * 7 + [9900.0, 0.0],
        )
        # 10,000 x 2.65 / 100 = 265.00; 9,900 x 2.65 / 100 = 262.35.
        self._assert_lines(slips[0], {"CA_NS_WCB": 265.0})
        self._assert_lines(slips[7], {"CA_NS_WCB": 262.35})
        self.assertNotIn("CA_NS_WCB", slips[8].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_NS_WCB")
        self.assertEqual(wcb.name, "WCB Nova Scotia Premium")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_NS_WCB_IE": 0.0, "CA_NS_WCB": 0.0})

    def test_wcb_2027_maximum(self):
        param = self.company._l10n_ca_param
        self.assertEqual(param("l10n_ca.ns.wcb.max_insurable", date(2026, 6, 1)), 79900)
        self.assertEqual(param("l10n_ca.ns.wcb.max_insurable", date(2027, 6, 1)), 83300)

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    def _watch(self, content):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_ns_payroll.source_wcb_ns_maximum")

        def fetch(self_, url, probe=False):
            return 200, content

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        return source

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wcb_ns_maximum(self):
        # 2027 in the sentence, 2026 in the table: both match the shipped
        # versions.
        source = self._watch(
            wcb_page(2027, "83,300", [(2026, "79,900"), (2025, "76,300")])
        )
        self.assertEqual(source.watch_state, "ok")
        self.assertIn(
            "l10n_ca.ns.wcb.max_insurable = 79900.0: matches.", source.watch_message
        )
        self.assertIn(
            "l10n_ca.ns.wcb.max_insurable = 83300.0: matches.", source.watch_message
        )
        # Before the next year is published, the sentence names 2026.
        source = self._watch(wcb_page(2026, "79,900", [(2025, "76,300")]))
        self.assertEqual(source.watch_state, "pending")
        self.assertIn("2027: not yet published.", source.watch_message)
        # A page without the sentence changed.
        source = self._watch(b"<html><body><p>Moved.</p></body></html>")
        self.assertEqual(source.watch_state, "changed")

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.ns.%")]
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
