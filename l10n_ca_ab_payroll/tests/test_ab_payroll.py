# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Alberta payslips checked against the T4127 formulas (option 1) and the
step-by-step examples of the T4032 for Alberta, January 2026.

Shipped 2026 parameters used by the derivations: rates 8% / 10% from
61,200 (KP 1,224) / 12% from 154,259 (KP 4,309) / 13% from 185,111 (KP
6,160) / 14% from 246,813 (KP 8,628) / 15% from 370,220 (KP 12,331); basic
personal amount 22,769 (K1P = 0.08 x 22,769 = 1,821.52); supplemental tax
credit K5P = ((K1P + K2P) - 4,896) x 0.25, at least 0; WCB-Alberta maximum
assessable earnings 110,900. The federal amounts are those of the tests of
l10n_ca_payroll: at 5,000 a month, C = 280.15, EI = 81.50, A = 59,434.99,
T1 = 5,338.28 and 444.86 of federal tax.

K2P = 0.08 x (min(P x C x 0.0495 / 0.0595, 3,519.45) + min(P x EI,
1,123.07)), the federal K2 items at the lowest Alberta rate.
"""

import io
from datetime import date
from pathlib import Path
from unittest.mock import patch

from freezegun import freeze_time
from reportlab.pdfgen import canvas

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ca_payroll.tools import sources_page

PREFIX = "l10n_ca.ab"


def _pdf(*lines):
    """Return the bytes of a one-page PDF that holds ``lines`` of text."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for index, line in enumerate(lines):
        pdf.drawString(72, 720 - 16 * index, line)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestAlbertaPayroll(AccountTestInvoicingCommon):
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
        cls.alberta = cls.env.ref("base.state_ca_ab")
        cls.journal = cls.company_data["default_journal_misc"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _contract(self, wage, **vals):
        employee = self.env["hr.employee"].create(
            {
                "name": "Alberta Test Employee",
                "birthday": "1985-06-15",
                "company_id": self.company.id,
            }
        )
        return self.env["hr.contract"].create(
            {
                "name": "Alberta Test Contract",
                "employee_id": employee.id,
                "company_id": self.company.id,
                "wage": wage,
                "date_start": "2026-01-01",
                "struct_id": self.structure.id,
                "schedule_pay": "monthly",
                "l10n_ca_province_id": self.alberta.id,
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
        self.assertTrue({"CA_AB_SAL", "CA_AB_WCB_IE", "CA_AB_WCB"} <= codes)
        rule = self.env.ref("l10n_ca_ab_payroll.rule_ab_wcb").with_company(self.company)
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
        self.assertEqual(contract.l10n_ca_prov_bpa, 22769.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        # A = 59,434.99 <= 61,200 -> V 0.08, KP 0
        #   K2P = 0.08 x (12 x 280.15 x 0.0495 / 0.0595 + 12 x 81.50)
        #       = 0.08 x (2,796.79 + 978) = 301.98
        #   K1P + K2P = 2,123.50 <= 4,896 -> K5P = 0
        #   T4 = 0.08 x 59,434.99 - 1,821.52 - 301.98 = 2,631.30
        # (5,338.28 + 2,631.30) / 12 = 664.13, of which 444.86 federal and
        # 219.27 Alberta.
        self._assert_lines(
            slip,
            {
                "CA_CPP": -280.15,
                "CA_EI": -81.50,
                "CA_FIT": -444.86,
                "CA_PIT": -219.27,
                "CA_AB_SAL": 5000.0,
                "CA_AB_WCB_IE": 5000.0,
            },
        )
        self.assertFalse(slip.l10n_ca_warning)
        tax_line = slip.line_ids.filtered(lambda line: line.code == "CA_PIT")
        self.assertIn("AB", tax_line.name)
        # The company has no WCB-Alberta rate: no premium line.
        self.assertNotIn("CA_AB_WCB", slip.line_ids.mapped("code"))
        slip.action_payslip_done()
        self.assertAlmostEqual(slip._l10n_ca_t4_values(2026)["box_22"], 664.13)

    def test_t4032_example_below_ympe(self):
        """Step-by-step example of the T4032 for Alberta, January 2026.

        1,300 a week with an RRSP contribution of 80 withheld at source:
        A = 52 x (1,300 - 12.33 - 80) = 62,798.84 -> V 0.10, KP 1,224.
        K2P = 0.08 x (52 x 73.35 x 0.0495 / 0.0595 + 52 x 21.19) = 342.00;
        K1P + K2P = 2,163.52 <= 4,896: no supplemental credit.
        T4 = 6,279.88 - 1,224 - 1,821.52 - 342.00 = 2,892.36 (the CRA shows
        2,892.37, its credits rounded first). The CRA gives 5,957.85 of
        federal tax: (5,957.85 + 2,892.36) / 52 = 170.20, the CRA's total,
        of which 114.57 federal and 55.63 Alberta.
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
                "CA_PIT": -55.63,
            },
        )

    def test_t4032_example_above_ympe(self):
        """Second example of the T4032 for Alberta: 1,600 a week, TD1AB of
        60,000, where the supplemental tax credit applies.

        The CPP and EI maximums are reached and the pay bears 64 of CPP2:
        A = 52 x 1,536 = 79,872 -> V 0.10, KP 1,224.
        K1P = 0.08 x 60,000 = 4,800; K2P = 0.08 x (3,519.45 + 1,123.07) =
        371.40; K5P = (5,171.40 - 4,896) x 0.25 = 68.85, the CRA's "2% x
        (64,642.52 - 61,200)". T4 = 7,987.20 - 1,224 - 5,171.40 - 68.85 =
        1,522.95. The CRA gives 9,406.39 federal: (9,406.39 + 1,522.95) / 52
        = 210.18, the CRA's total, of which 180.89 federal and 29.29
        Alberta. Without K5P it would be (9,406.39 + 1,591.80) / 52 =
        211.50.
        """
        # 6,933.33 x 12 / 52 = 1,600.00 a week.
        contract = self._contract(
            6933.33,
            schedule_pay="weekly",
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=60000.0,
        )
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
                "CA_PIT": -29.29,
            },
        )

    def test_supplemental_tax_credit(self):
        """K5P through the engine, above, at and below its threshold."""
        contract = self._contract(
            5000.0, l10n_ca_prov_td1_type="custom", l10n_ca_prov_td1_amount=60000.0
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        vals = slip._l10n_ca_compute(contract, 5000.0)
        # K1P = 0.08 x 60,000 = 4,800 and K2P = 371.4016:
        # K5P = (5,171.4016 - 4,896) x 0.25 = 68.8504
        self.assertAlmostEqual(
            slip._l10n_ca_prov_extra_credits(vals, PREFIX, 100000.0, 4800.0, 371.4016),
            68.8504,
            places=4,
        )
        # K1P + K2P = 4,896 exactly, or below it: no credit.
        self.assertEqual(
            slip._l10n_ca_prov_extra_credits(vals, PREFIX, 100000.0, 4500.0, 396.0),
            0.0,
        )
        self.assertEqual(
            slip._l10n_ca_prov_extra_credits(vals, PREFIX, 100000.0, 1821.52, 342.0),
            0.0,
        )
        # Another province's prefix keeps the credits of the engine.
        self.assertEqual(
            slip._l10n_ca_prov_extra_credits(
                vals, "l10n_ca.zz", 100000.0, 4800.0, 371.4016
            ),
            0.0,
        )
        # A = 100,000 -> V 0.10, KP 1,224:
        # T4 = 10,000 - 1,224 - 4,800 - 371.4016 - 68.8504 = 3,535.748
        result = slip._l10n_ca_prov_annual_tax(vals, PREFIX, 100000.0, 371.4016)
        self.assertAlmostEqual(result["basic_tax"], 3535.748, places=3)
        # The basic personal amount: K1P + K2P = 2,192.92, no K5P:
        # T4 = 10,000 - 1,224 - 1,821.52 - 371.4016 = 6,583.0784
        contract.l10n_ca_prov_td1_type = "basic"
        result = slip._l10n_ca_prov_annual_tax(vals, PREFIX, 100000.0, 371.4016)
        self.assertAlmostEqual(result["basic_tax"], 6583.0784, places=3)

    def test_claim_exempt_custom_and_additional_tax(self):
        contract = self._contract(5000.0, l10n_ca_prov_td1_type="exempt")
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": 0.0})
        # TD1AB claim 0, other credits 100 and 20 of additional tax:
        # K1P + K2P = 301.98 -> K5P = 0
        # T4 = 0.08 x 59,434.99 - 301.98 - 100 = 4,352.82
        # (5,338.28 + 4,352.82) / 12 = 807.59 -> 807.59 - 444.86 + 20
        contract = self._contract(
            5000.0,
            l10n_ca_prov_td1_type="custom",
            l10n_ca_prov_td1_amount=0.0,
            l10n_ca_prov_other_credits=100.0,
            l10n_ca_prov_additional_tax=20.0,
        )
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_FIT": -444.86, "CA_PIT": -382.73})

    def test_no_employer_tax_and_no_lcp(self):
        param = self.company._l10n_ca_param
        for key in ("employer_tax.rates", "lcp_rate", "credit_rate"):
            self.assertIsNone(param(f"{PREFIX}.{key}", date(2026, 6, 1), default=None))
        contract = self._contract(5000.0)
        slip = self._slip(contract, "2026-03-01", "2026-03-31")
        self.assertNotIn("CA_AB_ER_TAX", slip.line_ids.mapped("code"))

    # ------------------------------------------------------------------
    # WCB-Alberta
    # ------------------------------------------------------------------

    def test_wcb_up_to_the_maximum(self):
        self.env["l10n_ca.payroll.province.account"].create(
            {
                "company_id": self.company.id,
                "province_id": self.alberta.id,
                "wcb_rate": 1.46,
            }
        )
        contract = self._contract(12000.0)
        slips = self._monthly_slips(contract, range(1, 12))
        # 12,000 a month up to 110,900: September reaches 108,000, October
        # takes the 2,900 left, November nothing.
        self.assertEqual(
            [self._line(s, "CA_AB_WCB_IE") for s in slips],
            [12000.0] * 9 + [2900.0, 0.0],
        )
        # 12,000 x 1.46 / 100 = 175.20; 2,900 x 1.46 / 100 = 42.34
        self._assert_lines(slips[0], {"CA_AB_WCB": 175.20})
        self._assert_lines(slips[9], {"CA_AB_WCB": 42.34})
        self.assertNotIn("CA_AB_WCB", slips[10].line_ids.mapped("code"))
        wcb = slips[0].line_ids.filtered(lambda line: line.code == "CA_AB_WCB")
        self.assertEqual(wcb.name, "WCB-Alberta Premium")
        # A contract not covered has no assessable earnings.
        exempt = self._contract(12000.0, l10n_ca_wcb_exempt=True)
        slip = self._slip(exempt, "2026-03-01", "2026-03-31")
        self._assert_lines(slip, {"CA_AB_WCB_IE": 0.0, "CA_AB_WCB": 0.0})

    def test_parameters_of_2026(self):
        param = self.company._l10n_ca_param
        for day in (date(2026, 1, 1), date(2026, 7, 1)):
            self.assertEqual(param(f"{PREFIX}.bpa", day), 22769)
            self.assertEqual(
                param(f"{PREFIX}.supplemental_credit.threshold", day), 4896
            )
            self.assertEqual(param(f"{PREFIX}.supplemental_credit.rate", day), 0.25)
            self.assertEqual(param(f"{PREFIX}.wcb.max_insurable", day), 110900)
            self.assertEqual(param(f"{PREFIX}.brackets", day)[1], [61200, 0.1])

    # ------------------------------------------------------------------
    # Official sources
    # ------------------------------------------------------------------

    @freeze_time("2026-11-15")
    def test_watcher_of_the_wcb_fact_sheet(self):
        Source = type(self.env["l10n_ca.payroll.source"])
        source = self.env.ref("l10n_ca_ab_payroll.source_wcb_maximum_fact_sheet")
        content = _pdf(
            "Assessable earnings are the amount used to determine employer",
            "premiums. In 2025 the MAE is $106,400 and in 2026, the MAE",
            "is $110,900",
        )

        def fetch(self_, url, probe=False):
            return 200, content

        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        # 2026 matches the shipped version; 2027 is not on the sheet yet.
        self.assertEqual(source.watch_state, "pending")
        self.assertIn(
            "l10n_ca.ab.wcb.max_insurable = 110900.0: matches.", source.watch_message
        )
        # An HTML page instead of the PDF is a change of the source.
        content = b"<html><body><p>Page not found</p></body></html>"
        with patch.object(Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()
        self.assertEqual(source.watch_state, "changed")

    def test_official_sources(self):
        sources = self.env["l10n_ca.payroll.source"].search([])
        parameters = self.env["base.time.parameter"].search(
            [("code", "=like", "l10n_ca.ab.%")]
        )
        self.assertEqual(len(parameters), 5)
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
