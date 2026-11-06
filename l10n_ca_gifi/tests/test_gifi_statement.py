# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestGifiStatement(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ca")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.misc = cls.company_data["default_journal_misc"]
        cls.Statement = cls.env["l10n.ca.gifi.statement"]
        cls.dividends = cls.env["account.account"].create(
            {
                "code": "315000",
                "name": "Dividends declared",
                "account_type": "equity",
                "l10n_ca_gifi_code_id": cls.env.ref("l10n_ca_gifi.gifi_3700").id,
            }
        )

    # -- helpers -------------------------------------------------------

    def _account(self, code):
        return self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.company),
                ("code", "=", code),
            ],
            limit=1,
        )

    def _post(self, move_date, lines, journal=None):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": move_date,
                "journal_id": (journal or self.misc).id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "GIFI test",
                            "account_id": (
                                account
                                if not isinstance(account, str)
                                else self._account(account)
                            ).id,
                            "debit": debit,
                            "credit": credit,
                        }
                    )
                    for account, debit, credit in lines
                ],
            }
        )
        move.action_post()
        return move

    def _statement(self, year=2025):
        statement = self.Statement.create(
            {
                "company_id": self.company.id,
                "date_from": date(year, 1, 1),
                "date_to": date(year, 12, 31),
            }
        )
        statement.action_compute()
        return statement

    def _amounts(self, statement, schedule):
        return {
            line.code: line.amount
            for line in statement.line_ids
            if line.schedule == schedule
        }

    def _post_year(self):
        """One year of a service corporation, all entries in 2025."""
        self._post("2025-01-02", [("111200", 10000, 0), ("312100", 0, 10000)])
        self._post(
            "2025-03-15",
            [
                ("112110", 11497.50, 0),
                ("411200", 0, 10000),
                ("231000", 0, 500),
                ("232000", 0, 997.50),
            ],
        )
        self._post(
            "2025-04-10",
            [("512204", 2000.40, 0), ("118100", 100.02, 0), ("221110", 0, 2100.42)],
        )
        self._post("2025-06-30", [("124107", 3000, 0), ("111200", 0, 3000)])
        self._post("2025-11-30", [(self.dividends, 500, 0), ("111200", 0, 500)])
        self._post("2025-12-31", [("512201", 600, 0), ("124113", 0, 600)])
        self._post("2025-12-31", [("621000", 1000, 0), ("221210", 0, 1000)])

    # -- tests ---------------------------------------------------------

    def test_full_year(self):
        self._post_year()
        statement = self._statement()
        self.assertTrue(statement.first_year)
        self.assertFalse(
            statement.check_ids.filtered(lambda c: c.level == "error"),
            statement.check_ids.mapped("message"),
        )
        s100 = self._amounts(statement, "100")
        # Bank 10,000 - 3,000 - 500; receivable 11,497.50 rounds half up.
        self.assertEqual(s100["1002"], 6500)
        self.assertEqual(s100["1062"], 11498)
        self.assertEqual(s100["1066"], 100)
        # 1599 = 6,500 + 11,498 + 100.
        self.assertEqual(s100["1599"], 18098)
        # Contra account keeps the asset side: accumulated amortization < 0.
        self.assertEqual(s100["1740"], 3000)
        self.assertEqual(s100["1741"], -600)
        self.assertEqual(s100["2008"], 3000)
        self.assertEqual(s100["2009"], -600)
        # 2599 = 18,098 + 3,000 - 600.
        self.assertEqual(s100["2599"], 20498)
        # 2680 = GST 500 + QST 997.50 + income tax 1,000 = 2,497.50.
        self.assertEqual(s100["2621"], 2100)
        self.assertEqual(s100["2680"], 2498)
        self.assertEqual(s100["3139"], 4598)
        self.assertEqual(s100["3499"], 4598)
        # 3600 = 10,000 - 2,000.40 - 600 - 1,000 - 500 = 5,899.60.
        self.assertEqual(s100["3500"], 10000)
        self.assertEqual(s100["3600"], 5900)
        self.assertEqual(s100["3620"], 15900)
        self.assertEqual(s100["3640"], s100["2599"])
        # Roll-forward: 0 + 6,400 - 500 = 5,900 = 3600.
        self.assertNotIn("3660", s100)
        self.assertEqual(s100["3680"], 6400)
        self.assertEqual(s100["3700"], 500)
        self.assertEqual(s100["3849"], 5900)
        s125 = self._amounts(statement, "125")
        self.assertEqual(s125["8000"], 10000)
        self.assertEqual(s125["8299"], 10000)
        self.assertEqual(s125["8519"], 10000)
        # 9367 = sub-contracts 2,000 + amortization 600.
        self.assertEqual(s125["9110"], 2000)
        self.assertEqual(s125["8670"], 600)
        self.assertEqual(s125["9367"], 2600)
        self.assertEqual(s125["9368"], 2600)
        self.assertEqual(s125["9369"], 7400)
        self.assertEqual(s125["9970"], 7400)
        # 9999 = 7,400 - income taxes 1,000; taxes are subtracted.
        self.assertEqual(s125["9990"], 1000)
        self.assertEqual(s125["9999"], 6400)
        self.assertEqual(statement.total_assets, 20498)
        self.assertEqual(statement.net_income, 6400)
        # First year: Schedule 101 has the required items, all nil.
        self.assertEqual(
            self._amounts(statement, "101"), {"2599": 0, "3499": 0, "3620": 0}
        )
        # Revenue and assets under 1,000,000: GIFI-Short information.
        self.assertTrue(
            statement.check_ids.filtered(
                lambda c: c.level == "info" and "GIFI-Short" in c.message
            )
        )

    def test_csv_export(self):
        self._post_year()
        statement = self._statement()
        self.assertEqual(
            statement._csv_content("125").split("\r\n"),
            [
                "8000,10000",
                "8089,10000",
                "8299,10000",
                "8519,10000",
                "8670,600",
                "9110,2000",
                "9367,2600",
                "9368,2600",
                "9369,7400",
                "9970,7400",
                "9990,1000",
                "9999,6400",
                "",
            ],
        )
        s100 = statement._csv_content("100").split("\r\n")
        self.assertEqual(s100[0], "1002,6500")
        self.assertIn("1741,-600", s100)
        self.assertIn("3849,5900", s100)
        action = statement.with_context(gifi_schedule="100").action_export_csv()
        self.assertEqual(action["type"], "ir.actions.act_url")

    def test_closing_entries_ignored(self):
        self._post_year()
        before = self._amounts(self._statement(), "125")
        closing_journal = self.misc.copy({"code": "CLO", "name": "Closing"})
        # P&L closed into retained earnings: 10,000 - 2,000.40 - 600 - 1,000.
        self._post(
            "2025-12-31",
            [
                ("411200", 10000, 0),
                ("512204", 0, 2000.40),
                ("512201", 0, 600),
                ("621000", 0, 1000),
                ("322000", 0, 6399.60),
            ],
            journal=closing_journal,
        )
        self.company.l10n_ca_gifi_closing_journal_ids = closing_journal
        statement = self._statement()
        self.assertEqual(self._amounts(statement, "125"), before)
        self.assertEqual(self._amounts(statement, "100")["3600"], 5900)
        self.assertFalse(statement.error_count)

    def test_rounding_absorbed(self):
        # Bank 0.50 and receivable 0.50 each round to 1; revenue 1.00 -> 1.
        self._post(
            "2025-05-01",
            [("111200", 0.50, 0), ("112110", 0.50, 0), ("411200", 0, 1.00)],
        )
        statement = self._statement()
        s100 = self._amounts(statement, "100")
        # Assets 2 = liabilities 0 + equity: 3600 takes the 1 of rounding.
        self.assertEqual(s100["2599"], 2)
        self.assertEqual(s100["3600"], 2)
        # 3849 = 3680 (1) + 3740 (1 of rounding) = 3600.
        self.assertEqual(s100["3680"], 1)
        self.assertEqual(s100["3740"], 1)
        self.assertEqual(s100["3849"], 2)
        self.assertFalse(statement.error_count)
        self.assertEqual(
            len(
                statement.check_ids.filtered(lambda c: "rounding" in c.message.lower())
            ),
            2,
        )

    def test_unmapped_and_fallback(self):
        self.env.ref("l10n_ca_gifi.type_map_asset_current").unlink()
        unmapped = self.env["account.account"].create(
            {
                "code": "119990",
                "name": "Unmapped asset",
                "account_type": "asset_current",
            }
        )
        fallback = self.env["account.account"].create(
            {"code": "519990", "name": "Other expense", "account_type": "expense"}
        )
        self.assertEqual(unmapped.l10n_ca_gifi_mapping, "none")
        self.assertEqual(fallback.l10n_ca_gifi_mapping, "type")
        self.assertEqual(
            fallback.l10n_ca_gifi_effective_code_id,
            self.env.ref("l10n_ca_gifi.gifi_9270"),
        )
        self.assertIn(
            unmapped,
            self.env["account.account"].search([("l10n_ca_gifi_mapping", "=", "none")]),
        )
        # Default filter of the menu Accounts without GIFI Code: both the
        # fallback and the unmapped accounts are listed.
        listed = self.env["account.account"].search(
            [("l10n_ca_gifi_mapping", "in", ("type", "none"))]
        )
        self.assertIn(unmapped, listed)
        self.assertIn(fallback, listed)
        self._post("2025-02-01", [(unmapped, 100, 0), ("411200", 0, 100)])
        self._post("2025-02-02", [(fallback, 40, 0), ("111200", 0, 40)])
        statement = self._statement()
        errors = statement.check_ids.filtered(lambda c: c.level == "error")
        self.assertIn(unmapped, errors.account_id)
        # The unreported 100 of assets breaks 2599 = 3499 + 3620.
        self.assertTrue(errors.filtered(lambda c: c.gifi_code_id.code == "2599"))
        infos = statement.check_ids.filtered(lambda c: c.level == "info")
        self.assertIn(fallback, infos.account_id)
        self.assertEqual(self._amounts(statement, "125")["9270"], 40)

    def test_mapping_mismatch_warning(self):
        revenue = self._account("411200")
        revenue.l10n_ca_gifi_code_id = self.env.ref("l10n_ca_gifi.gifi_1480")
        self._post("2025-02-01", [("111200", 100, 0), (revenue, 0, 100)])
        statement = self._statement()
        warnings = statement.check_ids.filtered(lambda c: c.level == "warning")
        self.assertIn(revenue, warnings.account_id)

    def test_empty_year(self):
        statement = self._statement(2024)
        self.assertFalse(statement.error_count)
        s100 = self._amounts(statement, "100")
        self.assertEqual(s100, {"2599": 0, "3499": 0, "3620": 0, "3849": 0})
        self.assertEqual(
            self._amounts(statement, "125"),
            {"8299": 0, "9368": 0, "9369": 0, "9970": 0, "9999": 0},
        )

    def test_second_year_opening(self):
        self._post_year()
        self._post("2026-02-01", [("111200", 0, 300), ("512204", 300, 0)])
        statement = self._statement(2026)
        self.assertFalse(statement.first_year)
        self.assertFalse(self._amounts(statement, "101"))
        s100 = self._amounts(statement, "100")
        # 3660 = 3600 of 2025; 3849 = 5,900 - 300.
        self.assertEqual(s100["3660"], 5900)
        self.assertEqual(s100["3680"], -300)
        self.assertEqual(s100["3849"], 5600)
        self.assertEqual(s100["3600"], 5600)
        self.assertFalse(statement.error_count)

    def test_purchases_without_inventory_warning(self):
        # Vendor bill on the default expense account 511210 Purchases.
        self._post("2025-02-01", [("511210", 250, 0), ("221110", 0, 250)])
        self._post("2025-02-02", [("111200", 400, 0), ("411200", 0, 400)])
        statement = self._statement()
        self.assertEqual(self._amounts(statement, "125")["8320"], 250)
        warning = statement.check_ids.filtered(
            lambda c: c.level == "warning" and c.gifi_code_id.code == "8320"
        )
        self.assertTrue(warning)
        self.assertEqual(warning.account_id, self._account("511210"))
        # With inventory on the balance sheet, purchases are plausible.
        self._post("2025-03-01", [("121120", 100, 0), ("111200", 0, 100)])
        statement = self._statement()
        self.assertFalse(
            statement.check_ids.filtered(lambda c: c.gifi_code_id.code == "8320")
        )

    def test_full_year_no_purchases_warning(self):
        self._post_year()
        statement = self._statement()
        self.assertFalse(
            statement.check_ids.filtered(lambda c: c.gifi_code_id.code == "8320")
        )

    def test_other_comprehensive_income(self):
        oci = self.env["account.account"].create(
            {
                "code": "619990",
                "name": "Revaluation surplus",
                "account_type": "income_other",
                "l10n_ca_gifi_code_id": self.env.ref("l10n_ca_gifi.gifi_7000").id,
            }
        )
        self._post("2025-02-01", [("111200", 1000, 0), ("411200", 0, 1000)])
        self._post("2025-06-30", [("124101", 300, 0), (oci, 0, 300)])
        statement = self._statement()
        s100 = self._amounts(statement, "100")
        s125 = self._amounts(statement, "125")
        # 9999 = 1,000 + OCI 300; 3680 = 9999 - 9998 = 1,000.
        self.assertEqual(s125["9998"], 300)
        self.assertEqual(s125["9999"], 1300)
        self.assertEqual(s100["3680"], 1000)
        # OCI accumulates in 3580, net income in 3600.
        self.assertEqual(s100["3580"], 300)
        self.assertEqual(s100["3600"], 1000)
        self.assertEqual(s100["3849"], 1000)
        self.assertEqual(s100["2599"], 1300)
        self.assertFalse(statement.error_count, statement.check_ids.mapped("message"))

    def test_branch_not_selected(self):
        branch = self.env["res.company"].create(
            {"name": "GIFI branch", "parent_id": self.company.id}
        )
        self.env.user.company_ids |= branch
        statement = self.Statement.create(
            {
                "company_id": self.company.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 12, 31),
            }
        )
        with self.assertRaises(UserError):
            statement.with_context(
                allowed_company_ids=self.company.ids
            ).action_compute()
        statement.with_context(
            allowed_company_ids=(self.company | branch).ids
        ).action_compute()
        self.assertTrue(statement.computed_on)

    def test_gifi_short_threshold_parameter(self):
        self._post_year()
        # A company version of the asset limit below the 20,498 of assets.
        self.env["base.time.parameter"].create(
            {
                "name": "Asset limit",
                "code": "l10n_ca.gifi.short_max_assets",
                "type": "float",
                "company_id": self.company.id,
                "version_ids": [
                    Command.create({"date_from": "2025-01-01", "value": "20000"})
                ],
            }
        )
        statement = self._statement()
        self.assertFalse(
            statement.check_ids.filtered(lambda c: "GIFI-Short" in c.message)
        )

    def test_reports_render(self):
        self._post_year()
        statement = self._statement()
        pdf_report = self.env.ref("l10n_ca_gifi.action_report_gifi_statement")
        html = pdf_report._render_qweb_html(pdf_report.report_name, statement.ids)[0]
        # The report language follows the company partner, so the thousands
        # separator is a comma, a space or a no-break space.
        self.assertRegex(html, rb"20(,| |\xc2\xa0|\xe2\x80\xaf)498")
        xlsx, ext = (
            self.env["report.l10n_ca_gifi.statement_xlsx"]
            .with_context(active_model=statement._name)
            .create_xlsx_report(statement.ids, {})
        )
        self.assertEqual(ext, "xlsx")
        self.assertTrue(xlsx.startswith(b"PK"))

    def test_manager_without_full_accounting(self):
        # Accounting administrator of Community, without the technical
        # group "Show Full Accounting Features".
        user = new_test_user(
            self.env,
            login="gifi_manager",
            groups="base.group_user,account.group_account_manager",
            company_id=self.company.id,
            company_ids=self.company.ids,
        )
        self.assertFalse(user.has_group("account.group_account_user"))
        self._post_year()
        statement = (
            self.Statement.with_user(user)
            .with_context(allowed_company_ids=self.company.ids)
            .create(
                {
                    "company_id": self.company.id,
                    "date_from": date(2025, 1, 1),
                    "date_to": date(2025, 12, 31),
                }
            )
        )
        statement.action_compute()
        self.assertEqual(statement.total_assets, 20498)
        self.assertTrue(statement.check_ids)

    def test_french_number_format(self):
        self.env["res.lang"]._activate_lang("fr_CA")
        self._post_year()
        # Direct entry on retained earnings: warning with its amount.
        self._post("2025-12-20", [("321000", 1000, 0), ("111200", 0, 1000)])
        statement = self.Statement.with_context(lang="fr_CA").create(
            {
                "company_id": self.company.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 12, 31),
            }
        )
        statement.action_compute()
        warning = statement.check_ids.filtered(
            lambda c: c.gifi_code_id.code == "3740" and c.level == "warning"
        )
        self.assertIn("1\N{NO-BREAK SPACE}000,00", warning.message)
        # Whole-dollar amounts of the messages: French separators too.
        short = statement.check_ids.filtered(
            lambda c: c.level == "info" and "T1178" in c.message
        )
        self.assertIn("19\N{NO-BREAK SPACE}498", short.message)
        self.assertNotIn("19498", short.message)
        # 2599 = 20,498 - 1,000; French separators, not "19,498".
        pdf_report = self.env.ref("l10n_ca_gifi.action_report_gifi_statement")
        html = pdf_report.with_context(lang="fr_CA")._render_qweb_html(
            pdf_report.report_name, statement.ids
        )[0]
        self.assertIn("19\N{NO-BREAK SPACE}498".encode(), html)
        self.assertNotIn(b"19,498", html)
