# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Newfoundland and Labrador payslips checked against the T4127 formulas
(option 1) and the step-by-step examples of the T4032 for Newfoundland and
Labrador, January and July 2026.

Shipped 2026 parameters used by the derivations: rates 8.7% / 14.5% from
44,678 (KP 2,591) / 15.8% from 89,354 (KP 3,753) / 17.8% from 159,528 (KP
6,943) / 19.8% from 223,340 (KP 11,410) / 20.8% from 285,319 (KP 14,263) /
21.3% from 570,638 (KP 17,117) / 21.8% from 1,141,275 (KP 22,823); basic
personal amount 11,188 from January 1 (K1P = 0.087 x 11,188 = 973.36) and
15,000 from July 1 (K1P = 1,305.00); Health and Post-Secondary Education
Tax 2% above an exemption of 2,000,000; WorkplaceNL maximum assessable
earnings 80,935 (2027: 82,800). The federal amounts are those of the tests
of l10n_ca_payroll: at 5,000 a month, C = 280.15, EI = 81.50, A =
59,434.99, T1 = 5,338.28 and 444.86 of federal tax.

K2P = 0.087 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest provincial rate. At 5,000 a
month: 0.087 x (2,796.79 + 978) = 328.41.
"""

from datetime import date
from functools import partial
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page
from odoo.addons.l10n_ca_time_parameter.tools import bracket_constant

PREFIX = "l10n_ca.nl"


@tagged("post_install", "-at_install")
class TestNewfoundlandLabradorPayroll(AccountTestInvoicingCommon):
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
        cls.newfoundland = cls.env.ref("base.state_ca_nl")
        cls.journal = cls.company_data["default_journal_misc"]
        # Rate basis left at 0: the tax has one rate and an exemption for
        # every employer, so the basis selects nothing.
        cls.account = cls.env["l10n_ca.payroll.province.account"].create(
            {"company_id": cls.company.id, "province_id": cls.newfoundland.id}
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Newfoundland and Labrador Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Newfoundland and Labrador Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.newfoundland.id,
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
    # Set-up and parameters
    # ------------------------------------------------------------------

    def test_setup_rules_and_accounts(self):
        codes = set(self.structure.rule_ids.mapped("code"))
        self.assertTrue(
            {"CA_NL_SAL", "CA_NL_WCB_IE", "CA_NL_ER_TAX", "CA_NL_WCB"} <= codes
        )
        for xmlid in ("rule_nl_employer_tax", "rule_nl_wcb"):
            rule = self.env.ref(f"l10n_ca_nl_payroll.{xmlid}").with_company(
                self.company
            )
            self.assertEqual(rule.account_debit.code, "512121", xmlid)
            self.assertEqual(rule.account_credit.code, "221206", xmlid)
        count = len(self.structure.rule_ids)
        self.company.l10n_ca_payroll_setup()
        self.assertEqual(len(self.structure.rule_ids), count)
        self.assertTrue(self.account.has_employer_tax)

    def test_constants_and_basic_personal_amount(self):
        param = self.company._l10n_ca_param
        brackets = param(f"{PREFIX}.brackets", date(2026, 1, 1))
        # KP of table 8.1, derived from the thresholds and rounded; an
        # income equal to a threshold stays in the lower bracket, so each
        # bracket is read one dollar above its threshold.
        self.assertEqual(
            [round(bracket_constant(t + 1, brackets)) for t, _r in brackets],
            [0, 2591, 3753, 6943, 11410, 14263, 17117, 22823],
        )
        self.assertEqual(param(f"{PREFIX}.brackets", date(2026, 7, 1)), brackets)
        self.assertEqual(param(f"{PREFIX}.bpa", date(2026, 6, 30)), 11188)
        self.assertEqual(param(f"{PREFIX}.bpa", date(2026, 7, 1)), 15000)
        contract = self._contract(5000.0)
        self.assertTrue(contract.l10n_ca_prov_computed)

    # ------------------------------------------------------------------
    # Income tax
    # ------------------------------------------------------------------

    def test_monthly_5000(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,434.99, from 44,678 to 89,354 -> V 0.145, KP 2,591
        #   T4 = 0.145 x 59,434.99 - 2,591 - 973.36 - 328.41 = 4,725.31
        # (5,338.28 + 4,725.31) / 12 = 838.63, of which 444.86 federal and
        # 393.77 Newfoundland and Labrador.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -393.77,
                "CA_NL_SAL": 5000.0,
                "CA_NL_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("NL", tax_line.name)
        # Remuneration under the exemption and no WorkplaceNL rate: no
        # employer line.
        self.assertNotIn("CA_NL_ER_TAX", slip.line_ids.mapped("code"))
        self.assertNotIn("CA_NL_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 838.63)

    def test_monthly_5000_july(self):
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-07-01", "2026-07-31")
        # Prorated basic personal amount 15,000: K1P = 1,305.00
        #   T4 = 0.145 x 59,434.99 - 2,591 - 1,305.00 - 328.41 = 4,393.67
        # (5,338.28 + 4,393.67) / 12 = 811.00 -> 811.00 - 444.86 = 366.14
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -366.14})
        self.assertFalse(slip.l10n_ca_warning)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Newfoundland and Labrador,
        January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84. The CRA gives 5,957.85
        of federal tax and 5,169.56 of provincial tax for the year:
        11,127.41 / 52 = 213.99, of which 114.57 federal and 99.42
        provincial.
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
                "CA_PIT": -99.42,
            },
        )

    def test_t4032_example_below_ympe_july(self):
        """Same example in the T4032 for pays from July 1, 2026.

        The provincial credits rise from 1,345.27 to 1,676.92 (0.087 x
        (15,000 - 11,188) more): 4,837.91 of provincial tax and 10,795.76 /
        52 = 207.61, of which 114.57 federal and 93.04 provincial.
        """
        contract = self._contract(
            5633.33, schedule_pay="weekly", l10n_ca_rrsp_amount=80.0
        )
        slip = self._slip(contract, "2026-07-06", "2026-07-12")
        self._assert_lines(
            slip,
            {
                "BASIC": 1300.0,
                "CA_CPP": -73.35,
                "CA_EI": -21.19,
                "CA_FIT": -114.57,
                "CA_PIT": -93.04,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Newfoundland and Labrador:
        1,600 a week, January 2026.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872. The CRA gives 9,406.39 federal and 7,613.18
        provincial for the year: 17,019.57 / 52 = 327.30, of which 180.89
        federal and 146.41 provincial.
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
                "CA_PIT": -146.41,
            },
        )

    def test_t4032_example_above_ympe_july(self):
        """Second example of the T4032 for pays from July 1, 2026.

        The provincial credits rise from 1,377.26 to 1,708.90: 7,281.54 of
        provincial tax and 16,687.93 / 52 = 320.92, of which 180.89 federal
        and 140.03 provincial.
        """
        contract = self._contract(6933.33, schedule_pay="weekly")
        self._slip(contract, "2026-07-06", "2026-07-12", done=True, bonus=74400.0)
        slip = self._slip(contract, "2026-07-13", "2026-07-19")
        self._assert_lines(
            slip,
            {
                "CA_CPP": 0.0,
                "CA_CPP2": -64.0,
                "CA_EI": 0.0,
                "CA_FIT": -180.89,
                "CA_PIT": -140.03,
            },
        )

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1NL claim 0, other credits 120 and 20 of additional tax:
        # T4 = 0.145 x 59,434.99 - 2,591 - 328.41 - 120 = 5,578.67
        # (5,338.28 + 5,578.67) / 12 = 909.75 -> 909.75 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=120.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -484.89})

    def test_custom_claim_keeps_its_amount_in_july(self):
        """A TD1NL total claim entered on the contract is not raised on
        July 1: only the default claim follows the prorated amount."""
        contract = self._contract(
            5000.0, l10n_ca_prov_td1_type="custom", l10n_ca_prov_td1_amount=11188.0
        )
        # TCP 11,188 in July as in March: 393.77, the March amount of the
        # default claim (test_monthly_5000); the default claim gives 366.14.
        slip = self._slip(contract, "2026-07-01", "2026-07-31")
        self._assert_lines(slip, {"CA_PIT": -393.77})
        # Raised by the employer to 15,000 (11,188 + 3,812): 366.14.
        contract.l10n_ca_prov_td1_amount = 15000.0
        slip.compute_sheet()
        self._assert_lines(slip, {"CA_PIT": -366.14})

    # ------------------------------------------------------------------
    # Health and Post-Secondary Education Tax
    # ------------------------------------------------------------------

    def test_employer_tax_rate_and_exemption(self):
        day = date(2026, 6, 30)
        rate = partial(self.account._l10n_ca_employer_tax_rate, self.company, PREFIX)
        self.assertEqual(rate(0.0, day), 0.02)
        self.assertEqual(rate(2000000.01, day), 0.02)
        self.assertEqual(rate(50000000, day), 0.02)
        exemption = partial(
            self.account._l10n_ca_employer_tax_exemption, self.company, PREFIX
        )
        # Every employer keeps the exemption whatever its remuneration.
        self.assertEqual(exemption(0.0, day), 2000000)
        self.assertEqual(exemption(50000000, day), 2000000)
        # An associated employer takes its allocated share, at most the
        # exemption; without an allocation agreement, nothing.
        self.account.employer_tax_associated = True
        self.account.employer_tax_allocated_exemption = 2500000
        self.assertEqual(exemption(100000, day), 2000000)
        self.account.employer_tax_allocated_exemption = 800000
        self.assertEqual(exemption(100000, day), 800000)
        self.account.employer_tax_allocated_exemption = 0.0
        self.assertEqual(exemption(100000, day), 0.0)
        self.account.write(
            {"employer_tax_associated": False, "employer_tax_eligible": False}
        )
        self.assertEqual(exemption(100000, day), 0.0)

    def test_employer_tax_across_the_exemption(self):
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
            }
        )
        contract = self._contract(5000.0)
        january, february, march, april = self._monthly_slips(contract, (1, 2, 3, 4))
        # January 5,000 and February 10,000 cumulative: under 12,000.
        self._assert_lines(january, {"CA_NL_ER_TAX": 0.0, "CA_NL_SAL": 5000.0})
        self._assert_lines(february, {"CA_NL_ER_TAX": 0.0})
        self.assertNotIn("CA_NL_ER_TAX", january.line_ids.mapped("code"))
        # March: 15,000 - 12,000 = 3,000 taxable x 2% = 60.00
        # April: the whole 5,000 x 2% = 100.00
        self._assert_lines(march, {"CA_NL_ER_TAX": 60.0})
        self._assert_lines(april, {"CA_NL_ER_TAX": 100.0})
        line = march.line_ids.filtered(lambda line: line.code == "CA_NL_ER_TAX")
        self.assertTrue(line.name.startswith("Health and Post-Secondary Education"))
        self.assertRegex(line.name, r"\(2[.,]000%\)")

    def test_employer_tax_full_exemption(self):
        """An employer not associated deducts 2,000,000 whatever its size."""
        self.account.employer_tax_previous_payroll = 6000000.0
        contract = self._contract(900000.0)
        slips = self._monthly_slips(contract, (1, 2, 3, 4))
        # 900,000 and 1,800,000 cumulative: under 2,000,000.
        # March: 2,700,000 - 2,000,000 = 700,000 x 2% = 14,000.00
        # April: 900,000 x 2% = 18,000.00
        self.assertEqual(
            [self._line(s, "CA_NL_ER_TAX") for s in slips],
            [0.0, 0.0, 14000.0, 18000.0],
        )
        self.assertFalse(slips[2].l10n_ca_warning)

    def _march_batch(self):
        return self.env["hr.payslip.run"].create(
            {
                "name": "March 2026",
                "date_start": "2026-03-01",
                "date_end": "2026-03-31",
                "company_id": self.company.id,
            }
        )

    def test_employer_tax_batch_confirm_order(self):
        """Each pair of payslips of a batch shares the exemption once."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 5000.0,
            }
        )
        run = self._march_batch()
        first = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-31", run=run)
        second = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-31", run=run)
        self.assertLess(first.id, second.id)
        # The first payslip takes the whole exemption of 5,000; the second
        # counts it (R = 5,000) and bears 5,000 x 2% = 100.00.
        self._assert_lines(first, {"CA_NL_ER_TAX": 0.0})
        self._assert_lines(second, {"CA_NL_ER_TAX": 100.0})
        # Confirmed latest first, each payslip is recomputed: the second
        # still counts the first, and the first does not count the second.
        second.action_payslip_done()
        first.action_payslip_done()
        self._assert_lines(first, {"CA_NL_ER_TAX": 0.0})
        self._assert_lines(second, {"CA_NL_ER_TAX": 100.0})

    def test_employer_tax_batch_pay_date_order(self):
        """In a batch, a payslip paid earlier counts first, whatever its id."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 5000.0,
            }
        )
        run = self._march_batch()
        late = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-31", run=run)
        early = self._slip(self._contract(5000.0), "2026-03-01", "2026-03-15", run=run)
        self.assertLess(late.id, early.id)
        late.compute_sheet()
        # The payslip paid on March 15 takes the whole exemption of 5,000;
        # the one paid on March 31 counts it and bears 100.00, in either
        # confirmation order.
        for slip in (late, early, None):
            self._assert_lines(early, {"CA_NL_ER_TAX": 0.0})
            self._assert_lines(late, {"CA_NL_ER_TAX": 100.0})
            if slip:
                slip.action_payslip_done()

    def test_employer_tax_credit_note(self):
        """A credit-note payslip reverses the tax of the pay it takes back."""
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
            }
        )
        contract = self._contract(5000.0)
        self._monthly_slips(contract, (1, 2, 3))
        refund = self._slip(
            contract, "2026-03-01", "2026-03-28", done=True, credit_note=True
        )
        # R = 15,000; the credit note takes G = 5,000 out of it:
        # tax = 2% x (max(0, 15,000 - 12,000) - max(0, 10,000 - 12,000))
        #     = 2% x 3,000 = 60.00, the tax of March, counted negatively.
        self._assert_lines(refund, {"CA_NL_SAL": 5000.0, "CA_NL_ER_TAX": 60.0})
        # R = 10,000: April uses the 2,000 of exemption left and bears
        # 3,000 x 2% = 60.00.
        april = self._slip(contract, "2026-04-01", "2026-04-28")
        self._assert_lines(april, {"CA_NL_ER_TAX": 60.0})

    def test_employer_tax_refund_and_negative_earnings(self):
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 12000.0,
            }
        )
        contract = self._contract(5000.0)
        march = self._monthly_slips(contract, (1, 2, 3))[-1]
        april = self._slip(contract, "2026-04-01", "2026-04-28")
        # R = 15,000: April bears 5,000 x 2% = 100.00.
        self._assert_lines(april, {"CA_NL_ER_TAX": 100.0})
        # A recovery entered as negative earnings keeps its sign:
        # -2,000 -> taxable max(0, 13,000 - 12,000) - (15,000 - 12,000) =
        # -2,000 -> -40.00; -4,000 only reverses the 3,000 above the
        # exemption -> -60.00.
        vals = april._l10n_ca_compute(contract, -2000.0)
        self.assertAlmostEqual(vals["province_remuneration"], -2000.0)
        self.assertAlmostEqual(vals["employer_tax"], -40.0)
        vals = april._l10n_ca_compute(contract, -4000.0)
        self.assertAlmostEqual(vals["employer_tax"], -60.0)
        self.assertAlmostEqual(vals["wcb_insurable"], 0.0)
        # The refund of March counts negatively: R = 10,000 and April
        # bears max(0, 15,000 - 12,000) x 2% = 60.00.
        march.refund_sheet()
        april.compute_sheet()
        self._assert_lines(april, {"CA_NL_ER_TAX": 60.0})

    def test_employer_tax_without_exemption(self):
        contract = self._contract(5000.0)
        # Associated without an allocation agreement: no exemption, 2% x
        # 5,000 = 100.00 from the first pay.
        self.account.write(
            {
                "employer_tax_associated": True,
                "employer_tax_allocated_exemption": 0.0,
            }
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_NL_ER_TAX": 100.0})
        # Not eligible: the same.
        self.account.write(
            {"employer_tax_associated": False, "employer_tax_eligible": False}
        )
        slip.compute_sheet()
        self._assert_lines(slip, {"CA_NL_ER_TAX": 100.0})

    def test_employer_tax_basis_warning(self):
        """The rate basis left at 0 warns only when it selects something."""
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self.assertFalse(slip.l10n_ca_warning)
        # A version with an exemption threshold makes the basis decide the
        # exemption: the basis left at 0 is then reported.
        parameter = self.env["base.time.parameter"].create(
            {
                "name": "Threshold of the test",
                "code": f"{PREFIX}.employer_tax.exemption_threshold",
                "type": "float",
                "company_id": self.company.id,
                "country_id": self.env.ref("base.ca").id,
            }
        )
        self.env["base.time.parameter.version"].create(
            {
                "parameter_id": parameter.id,
                "date_from": "2026-01-01",
                "value": "5000000",
            }
        )
        slip.compute_sheet()
        self.assertIn(
            f"The total remuneration of {self.company.name} in Newfoundland and "
            "Labrador that sets the employer payroll tax is 0",
            slip.l10n_ca_warning,
        )

    # ------------------------------------------------------------------
    # WorkplaceNL
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.account.wcb_rate = 1.20
        contract = self._contract(10000.0)
        slips = self._monthly_slips(contract, range(1, 11))
        # 10,000 a month up to 80,935: August reaches 80,000, September
        # takes the 935 left, October nothing.
        self.assertEqual(
            [self._line(s, "CA_NL_WCB_IE") for s in slips],
            [10000.0] * 8 + [935.0, 0.0],
        )
        # 1.20 x 10,000 / 100 = 120.00; 1.20 x 935 / 100 = 11.22
        self._assert_lines(slips[0], {"CA_NL_WCB": 120.0})
        self._assert_lines(slips[8], {"CA_NL_WCB": 11.22})
        self.assertNotIn("CA_NL_WCB", slips[9].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_NL_WCB")
        self.assertEqual(wcb.name, "WorkplaceNL Assessment")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(10000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_NL_WCB_IE": 0.0, "CA_NL_WCB": 0.0})

    def test_wcb_2027_maximum(self):
        param = self.company._l10n_ca_param
        code = f"{PREFIX}.wcb.max_insurable"
        self.assertEqual(param(code, date(2026, 6, 1)), 80935)
        self.assertEqual(param(code, date(2027, 6, 1)), 82800)

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    @staticmethod
    def _annual_assessment_page(years, amounts):
        cells = "".join(f"<td>{year} </td>" for year in years)
        values = "".join(f"<td>${value} </td>" for value in amounts)
        return (
            "<html><body><p><strong>Maximum Assessable Earnings "
            f"2021-{years[-1]}</strong></p><figure><table><tbody>"
            f"<tr>{cells}</tr><tr>{values}</tr></tbody></table></figure>"
            "</body></html>"
        ).encode()

    def _watch(self, page):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_nl_payroll.source_workplacenl_annual_assessment")

        def fetch(self_, url, probe=False):
            return 200, page

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        return source

    @freeze_time("2026-11-15")
    def test_watcher_of_the_annual_assessment_page(self):
        source = self._watch(
            self._annual_assessment_page(
                (2022, 2023, 2024, 2025, 2026, 2027),
                ("69,005", "72,870", "76,955", "79,345", "80,935", "82,800"),
            )
        )
        # Both years match the shipped versions.
        self.assertEqual(source.watch_state, "ok")
        self.assertIn(
            "l10n_ca.nl.wcb.max_insurable = 80935.0: matches.", source.watch_message
        )
        self.assertIn(
            "l10n_ca.nl.wcb.max_insurable = 82800.0: matches.", source.watch_message
        )
        # Before the November update, the next year is not on the page yet.
        source = self._watch(
            self._annual_assessment_page(
                (2022, 2023, 2024, 2025, 2026),
                ("69,005", "72,870", "76,955", "79,345", "80,935"),
            )
        )
        self.assertEqual(source.watch_state, "pending")
        # A page without the table has changed.
        source = self._watch(b"<html><body><p>Annual Assessment</p></body></html>")
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
