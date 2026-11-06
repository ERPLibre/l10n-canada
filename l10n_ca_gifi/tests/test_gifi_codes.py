# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import csv

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestGifiCodes(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ca")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.Code = cls.env["l10n.ca.gifi.code"].with_context(active_test=False)

    def _code(self, code):
        return self.env.ref(f"l10n_ca_gifi.gifi_{code}")

    def test_index_loaded(self):
        # Appendix A of RC4088 (Rev. 23): 766 items from 1000 to 9999.
        self.assertEqual(self.Code.search_count([]), 766)
        totals = [
            "1599",
            "2008",
            "2009",
            "2178",
            "2179",
            "2589",
            "2599",
            "3139",
            "3450",
            "3499",
            "3620",
            "3640",
            "3660",
            "3680",
            "3849",
            "8089",
            "8299",
            "8518",
            "8519",
            "9367",
            "9368",
            "9369",
            "9659",
            "9898",
            "9899",
            "9970",
            "9998",
            "9999",
        ]
        for code in totals:
            self.assertTrue(self._code(code).is_total, code)
        self.assertFalse(self._code("3600").is_total)
        self.assertTrue(self._code("3575").partnership_only)
        self.assertFalse(self._code("3575").active)

    def test_tree(self):
        self.assertEqual(self._code("1062").total_id, self._code("1599"))
        self.assertEqual(self._code("1062").parent_id, self._code("1060"))
        self.assertEqual(self._code("1063").parent_id, self._code("1061"))
        self.assertEqual(self._code("1741").total_id, self._code("2009"))
        self.assertEqual(self._code("2013").total_id, self._code("2179"))
        self.assertEqual(self._code("8500").total_sign, -1)
        self.assertEqual(self._code("8500").total_id, self._code("8518"))
        self.assertEqual(self._code("9368").total_sign, -1)
        self.assertEqual(self._code("9990").total_sign, -1)
        self.assertEqual(self._code("3700").total_sign, -1)
        self.assertEqual(
            self._code("8519")._formula_terms(), [(1, "8089"), (-1, "8518")]
        )
        # Every active detail item rolls into a total.
        orphans = self.Code.search(
            [("active", "=", True), ("is_total", "=", False), ("total_id", "=", False)]
        )
        self.assertFalse(orphans, orphans.mapped("code"))

    def test_code_constraints(self):
        with self.assertRaises(ValidationError):
            self.Code.create(
                {"code": "12A4", "name": "Bad", "category": "asset", "schedule": "100"}
            )
        account = self.company_data["default_account_revenue"]
        with self.assertRaises(ValidationError):
            account.l10n_ca_gifi_code_id = self._code("8299")

    def test_ca_2023_chart_mapped(self):
        with file_open("l10n_ca/data/template/account.account-ca_2023.csv") as f:
            xmlids = [row["id"] for row in csv.DictReader(f)]
        self.assertEqual(len(xmlids), 341)
        chart = self.env["account.chart.template"].with_company(self.company)
        missing = [
            xmlid for xmlid in xmlids if not chart.ref(xmlid).l10n_ca_gifi_code_id
        ]
        self.assertFalse(missing)
        self.assertEqual(
            chart.ref("l10n_ca_111200").l10n_ca_gifi_code_id, self._code("1002")
        )
        self.assertEqual(
            chart.ref("l10n_ca_512201").l10n_ca_gifi_code_id, self._code("8670")
        )
        self.assertEqual(
            chart.ref("l10n_ca_511300").l10n_ca_gifi_code_id, self._code("8500")
        )
        # Accumulated amortization of deferred charges is a contra item.
        self.assertEqual(
            chart.ref("l10n_ca_131120").l10n_ca_gifi_code_id, self._code("2425")
        )
        # Accounts created by the chart loader outside the template.
        self.assertEqual(
            self.company.account_journal_suspense_account_id.l10n_ca_gifi_code_id,
            self._code("1002"),
        )
        bank = self.company_data["default_journal_bank"]
        self.assertEqual(
            bank.default_account_id.l10n_ca_gifi_code_id, self._code("1002")
        )

    def test_assign_existing_company(self):
        chart = self.env["account.chart.template"].with_company(self.company)
        account = chart.ref("l10n_ca_411200")
        other = chart.ref("l10n_ca_411100")
        account.l10n_ca_gifi_code_id = False
        other.l10n_ca_gifi_code_id = self._code("8230")
        self.company._l10n_ca_gifi_assign_default_codes()
        self.assertEqual(account.l10n_ca_gifi_code_id, self._code("8000"))
        # A code chosen by the user is kept.
        self.assertEqual(other.l10n_ca_gifi_code_id, self._code("8230"))

    def test_type_map_company_wins(self):
        Map = self.env["l10n.ca.gifi.account.type.map"]
        self.assertEqual(Map._get_type_map(self.company)["expense"], self._code("9270"))
        self.assertEqual(
            Map._get_type_map(self.company)["expense_direct_cost"], self._code("8450")
        )
        Map.create(
            {
                "account_type": "expense",
                "gifi_code_id": self._code("9284").id,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(Map._get_type_map(self.company)["expense"], self._code("9284"))
        with self.assertRaises(ValidationError):
            Map.create(
                {
                    "account_type": "expense",
                    "gifi_code_id": self._code("9270").id,
                    "company_id": self.company.id,
                }
            )

    def test_type_map_selection_translated(self):
        # The account types of the fallback list follow the user language.
        self.env["res.lang"]._activate_lang("fr_CA")
        selection = self.env["ir.model.fields.selection"].search(
            [
                ("field_id.model", "=", "account.account"),
                ("field_id.name", "=", "account_type"),
                ("value", "=", "asset_cash"),
            ]
        )
        selection.with_context(lang="fr_CA").name = "Banque et encaisse"
        Map = self.env["l10n.ca.gifi.account.type.map"].with_context(lang="fr_CA")
        labels = dict(Map.fields_get(["account_type"])["account_type"]["selection"])
        self.assertEqual(labels["asset_cash"], "Banque et encaisse")
