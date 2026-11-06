# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCca(AccountTestInvoicingCommon):
    """Expected amounts are derived by hand from Reg. 1100 with the shipped
    parameters; each test states its derivation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.write(
            {
                "l10n_ca_ccpc": True,
                "fiscalyear_last_month": "12",
                "fiscalyear_last_day": 31,
            }
        )
        cls.profile = cls.env["account.asset.profile"].create(
            {
                "name": "Equipment - 5 years",
                "account_expense_depreciation_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "account_depreciation_id": cls.company_data[
                    "default_account_assets"
                ].id,
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
                "prorata": False,
            }
        )
        cls.Schedule = cls.env["l10n.ca.cca.schedule"]

    def _class(self, number):
        return self.env.ref("l10n_ca_cca.cca_class_" + number.replace(".", "_"))

    def _asset(self, number, cost, start, **values):
        vals = {
            "name": f"Class {number} asset",
            "profile_id": self.profile.id,
            "purchase_value": cost,
            "date_start": start,
            "l10n_ca_cca_class_id": self._class(number).id,
        }
        vals.update(values)
        asset = self.env["account.asset"].create(vals)
        asset.validate()
        return asset

    def _schedule(self, year, generate=True, **values):
        vals = {
            "company_id": self.company.id,
            "date_from": date(year, 1, 1),
            "date_to": date(year, 12, 31),
        }
        vals.update(values)
        schedule = self.Schedule.create(vals)
        if generate:
            schedule.action_generate()
        return schedule

    def _line(self, schedule, number, asset=None):
        return schedule.line_ids.filtered(
            lambda line: line.class_id == self._class(number)
            and (not asset or line.asset_id == asset)
        )

    def test_shipped_parameters(self):
        param = self.company._l10n_ca_param
        self.assertEqual(param("l10n_ca.cca.class_50.rate", date(2026, 6, 1)), 0.55)
        self.assertEqual(param("l10n_ca.cca.class_8.rate", date(2025, 6, 1)), 0.20)
        self.assertEqual(
            param("l10n_ca.cca.class_10_1.cost_limit", date(2025, 6, 1)), 38000.0
        )
        self.assertEqual(
            param("l10n_ca.cca.class_10_1.cost_limit", date(2026, 6, 1)), 39000.0
        )
        self.assertEqual(
            param("l10n_ca.cca.class_54.cost_limit", date(2026, 6, 1)), 61000.0
        )

    def test_class_50_computer_2026_fully_expensed(self):
        # Acquired and available for use after 2024-04-15 and before 2027:
        # 100% first-year write-off. Max CCA = 3,000 x 100% = 3,000.
        computer = self._asset("50", 3000.0, "2026-03-01")
        self.assertTrue(computer.l10n_ca_cca_immediate_expensing)
        schedule = self._schedule(2026)
        line = self._line(schedule, "50")
        self.assertEqual(line.additions_expensing, 3000.0)
        self.assertAlmostEqual(line.max_cca, 3000.0)
        self.assertAlmostEqual(line.cca_claimed, 3000.0)
        self.assertAlmostEqual(line.closing_ucc, 0.0)

    def test_class_50_available_2027_gets_riip(self):
        # Available for use in 2027: no immediate expensing. Class 50 is
        # out of the general RIIP factor 1/2 and its own factor is nil
        # after 2026 (Reg. 1100(2), A.1(e)(ii)), while the half-year rule
        # does not apply to RIIP: base = 2,000 x 1.0 = 2,000; max = 55% x
        # 2,000 = 1,100; closing 900.
        computer = self._asset(
            "50",
            2000.0,
            "2027-01-10",
            l10n_ca_cca_acquisition_date="2026-12-15",
        )
        self.assertFalse(computer.l10n_ca_cca_immediate_expensing)
        line = self._line(self._schedule(2027), "50")
        self.assertEqual(line.additions_enhanced, 2000.0)
        self.assertAlmostEqual(line.cca_base, 2000.0)
        self.assertAlmostEqual(line.max_cca, 1100.0)
        self.assertAlmostEqual(line.closing_ucc, 900.0)

    def test_class_50_available_2024_expensed(self):
        # Acquired and available for use after 2024-04-15: 100% in 2024.
        computer = self._asset("50", 1500.0, "2024-06-03")
        self.assertTrue(computer.l10n_ca_cca_immediate_expensing)
        line = self._line(self._schedule(2024), "50")
        self.assertEqual(line.additions_expensing, 1500.0)
        self.assertAlmostEqual(line.max_cca, 1500.0)

    def test_manufacturing_expensing_windows(self):
        end = date(2026, 12, 31)

        def rate(number, acquired, available):
            return self._class(number)._expensing_rate(
                self.company, acquired, available, end, "federal"
            )

        # Class 53 acquired in 2025: factor 1 on 50% whenever available
        # before 2034 (A.1(f)(i)).
        self.assertEqual(rate("53", date(2025, 3, 1), date(2031, 1, 5)), 1.0)
        self.assertEqual(rate("53", date(2025, 3, 1), date(2034, 1, 5)), 0.0)
        # Class 53 acquired in 2024 (AIIP): 75% in 2025, 55% in 2026.
        self.assertEqual(rate("53", date(2024, 3, 1), date(2025, 1, 5)), 0.75)
        self.assertEqual(rate("53", date(2024, 3, 1), date(2026, 1, 5)), 0.55)
        # Class 43 acquired after 2025: 100% / 75% / 55% (A.1(f)(ii)-(iv)).
        self.assertEqual(rate("43", date(2026, 3, 1), date(2026, 4, 1)), 1.0)
        self.assertEqual(rate("43", date(2026, 3, 1), date(2030, 4, 1)), 0.75)
        self.assertEqual(rate("43", date(2026, 3, 1), date(2033, 4, 1)), 0.55)
        self.assertEqual(rate("43", date(2025, 3, 1), date(2026, 4, 1)), 0.0)

    def test_class_8_half_year_and_riip(self):
        # Desk (RIIP): 10,000 x 0.5 x 3 = 15,000 in the base.
        # Used desk from a related company (no incentive, half-year rule):
        # 4,000 x 0.5 = 2,000. Max = 20% x 17,000 = 3,400.
        # UCC before CCA = 14,000; closing = 14,000 - 3,400 = 10,600.
        self._asset("8", 10000.0, "2026-05-01")
        self._asset("8", 4000.0, "2026-05-01", l10n_ca_cca_enhancement_excluded=True)
        line = self._line(self._schedule(2026), "8")
        self.assertEqual(line.additions_enhanced, 10000.0)
        self.assertEqual(line.additions_regular, 4000.0)
        self.assertAlmostEqual(line.cca_base, 17000.0)
        self.assertAlmostEqual(line.max_cca, 3400.0)
        self.assertAlmostEqual(line.closing_ucc, 10600.0)

    def test_aiip_windows(self):
        furniture = self._class("8")
        multiplier = furniture._aiip_multiplier
        end_2026 = date(2026, 12, 31)
        # RIIP, full incentive / phase-out / ended.
        self.assertEqual(
            multiplier(
                self.company, date(2026, 1, 5), date(2026, 2, 1), end_2026, "federal"
            ),
            3.0,
        )
        self.assertEqual(
            multiplier(
                self.company, date(2026, 1, 5), date(2030, 2, 1), end_2026, "federal"
            ),
            2.0,
        )
        self.assertEqual(
            multiplier(
                self.company, date(2026, 1, 5), date(2034, 2, 1), end_2026, "federal"
            ),
            1.0,
        )
        # Acquired in 2024, available in 2025: original AII phase-out.
        self.assertEqual(
            multiplier(
                self.company, date(2024, 6, 1), date(2025, 2, 1), end_2026, "federal"
            ),
            2.0,
        )
        # Classes 44, 46 and 50 out of the expensing window: nil factor,
        # full cost without the half-year rule, 2 times.
        for number in ("44", "46", "50"):
            self.assertEqual(
                self._class(number)._aiip_multiplier(
                    self.company,
                    date(2026, 1, 5),
                    date(2028, 2, 1),
                    end_2026,
                    "federal",
                ),
                2.0,
            )
        # Class 14 is not under the half-year rule: 1.5 times.
        self.assertEqual(
            self._class("14")._aiip_multiplier(
                self.company, date(2026, 1, 5), date(2026, 2, 1), end_2026, "federal"
            ),
            1.5,
        )

    def test_class_12_factor_capped_at_cost(self):
        # Tool of 400 (< 500 threshold): exempt from the half-year rule,
        # first-year factor 1 x 3, capped at 1 / 100%. Software of 1,000
        # previously owned: half-year rule, 0.5. Max = 400 + 500 = 900.
        tool = self._asset("12", 400.0, "2026-04-01")
        self.assertTrue(tool.l10n_ca_cca_half_year_exempt)
        self._asset("12", 1000.0, "2026-04-01", l10n_ca_cca_enhancement_excluded=True)
        line = self._line(self._schedule(2026), "12")
        self.assertAlmostEqual(line.max_cca, 900.0)
        self.assertAlmostEqual(line.closing_ucc, 500.0)

    def test_disposal_recapture_terminal_loss_capital_gain(self):
        car = self._asset("10", 20000.0, "2023-06-01")
        desk = self._asset("8", 6000.0, "2023-06-01")
        lot = self._asset("17", 20000.0, "2023-06-01")
        schedule = self._schedule(2026, generate=False)
        self.env["l10n.ca.cca.schedule.line"].create(
            [
                {
                    "schedule_id": schedule.id,
                    "class_id": self._class(n).id,
                    "opening_ucc": u,
                }
                for n, u in (("10", 5000.0), ("8", 5000.0), ("17", 12000.0))
            ]
        )
        car.write(
            {"l10n_ca_cca_disposal_date": "2026-08-01", "l10n_ca_cca_proceeds": 8000.0}
        )
        desk.write(
            {"l10n_ca_cca_disposal_date": "2026-08-01", "l10n_ca_cca_proceeds": 1000.0}
        )
        lot.write(
            {"l10n_ca_cca_disposal_date": "2026-08-01", "l10n_ca_cca_proceeds": 25000.0}
        )
        schedule.action_generate()
        # Class 10: 5,000 - min(8,000, 20,000) = -3,000 -> recapture 3,000.
        line = self._line(schedule, "10")
        self.assertAlmostEqual(line.dispositions, 8000.0)
        self.assertAlmostEqual(line.recapture, 3000.0)
        self.assertAlmostEqual(line.max_cca, 0.0)
        self.assertAlmostEqual(line.closing_ucc, 0.0)
        # Class 8: last property sold, 5,000 - 1,000 = 4,000 terminal loss.
        line = self._line(schedule, "8")
        self.assertFalse(line.property_remaining)
        self.assertAlmostEqual(line.terminal_loss, 4000.0)
        self.assertAlmostEqual(line.max_cca, 0.0)
        self.assertAlmostEqual(line.closing_ucc, 0.0)
        # Class 17: proceeds above cost: dispositions limited to the cost
        # 20,000; 12,000 - 20,000 = -8,000 recapture; capital gain 5,000.
        line = self._line(schedule, "17")
        self.assertAlmostEqual(line.dispositions, 20000.0)
        self.assertAlmostEqual(line.recapture, 8000.0)
        self.assertAlmostEqual(line.capital_gain, 5000.0)
        self.assertAlmostEqual(schedule.total_recapture, 11000.0)
        self.assertAlmostEqual(schedule.total_terminal_loss, 4000.0)

    def test_removal_wizard_sets_proceeds(self):
        asset = self._asset("8", 1000.0, "2026-01-01")
        wizard = (
            self.env["account.asset.remove"]
            .with_context(active_id=asset.id, early_removal=True)
            .create(
                {
                    "date_remove": "2026-01-31",
                    "sale_value": 400.0,
                    "posting_regime": "gain_loss_on_sale",
                    "account_sale_id": self.company_data["default_account_assets"].id,
                    "account_plus_value_id": self.company_data[
                        "default_account_revenue"
                    ].id,
                    "account_min_value_id": self.company_data[
                        "default_account_expense"
                    ].id,
                }
            )
        )
        wizard.remove()
        self.assertEqual(asset.l10n_ca_cca_proceeds, 400.0)
        self.assertEqual(asset.l10n_ca_cca_disposal_date, date(2026, 1, 31))
        # Acquired and disposed in the same year, last of its class:
        # UCC = 1,000 - 400 = 600, terminal loss 600.
        line = self._line(self._schedule(2026), "8")
        self.assertAlmostEqual(line.terminal_loss, 600.0)

    def test_carry_forward_and_lock(self):
        # 2025: RIIP desk 10,000 -> max 20% x 15,000 = 3,000; 2,000 claimed,
        # closing 8,000. 2026: opening 8,000, max 20% x 8,000 = 1,600.
        self._asset("8", 10000.0, "2025-06-01")
        first = self._schedule(2025)
        line = self._line(first, "8")
        self.assertAlmostEqual(line.max_cca, 3000.0)
        line.cca_claimed = 2000.0
        self.assertAlmostEqual(line.closing_ucc, 8000.0)
        first.action_lock()
        with self.assertRaises(UserError):
            line.cca_claimed = 1000.0
        second = self._schedule(2026)
        self.assertEqual(second.previous_id, first)
        line = self._line(second, "8")
        self.assertAlmostEqual(line.opening_ucc, 8000.0)
        self.assertAlmostEqual(line.max_cca, 1600.0)
        self.assertAlmostEqual(line.closing_ucc, 6400.0)
        second.action_lock()
        with self.assertRaises(UserError):
            first.action_unlock()
        second.action_unlock()
        first.action_unlock()
        self.assertEqual(first.state, "draft")

    def test_class_10_1_separate_class_and_disposal(self):
        # 2026: cost 50,000 limited to 39,000; RIIP 0.5 x 3: max =
        # 30% x 1.5 x 39,000 = 17,550, closing 21,450.
        car = self._asset("10.1", 50000.0, "2026-02-01")
        self.assertEqual(car.l10n_ca_cca_capital_cost, 39000.0)
        first = self._schedule(2026)
        line = self._line(first, "10.1", car)
        self.assertEqual(line.asset_id, car)
        self.assertAlmostEqual(line.max_cca, 17550.0)
        self.assertAlmostEqual(line.closing_ucc, 21450.0)
        first.action_lock()
        # 2027: sold; half of the allowance on the opening balance, 50% x
        # 30% x 21,450 = 3,217.50, no recapture nor terminal loss.
        car.write(
            {"l10n_ca_cca_disposal_date": "2027-06-30", "l10n_ca_cca_proceeds": 30000.0}
        )
        line = self._line(self._schedule(2027), "10.1", car)
        self.assertAlmostEqual(line.max_cca, 3217.5)
        self.assertAlmostEqual(line.recapture, 0.0)
        self.assertAlmostEqual(line.terminal_loss, 0.0)
        self.assertAlmostEqual(line.closing_ucc, 0.0)

    def test_book_to_tax_reconciliation(self):
        # Book: 10,000 straight-line over 5 years = 2,000 for 2026.
        # Tax: RIIP 20% x 1.5 x 10,000 = 3,000. Schedule 1 net = 2,000 -
        # 3,000 = -1,000.
        asset = self._asset("8", 10000.0, "2026-01-01")
        year_line = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate" and line.line_date.year == 2026
        )
        year_line.create_move()
        schedule = self._schedule(2026)
        line = self._line(schedule, "8")
        self.assertAlmostEqual(line.book_depreciation, 2000.0)
        self.assertAlmostEqual(line.cca_claimed, 3000.0)
        self.assertAlmostEqual(line.book_tax_difference, -1000.0)
        self.assertAlmostEqual(schedule.total_book_depreciation, 2000.0)
        self.assertAlmostEqual(schedule.schedule1_adjustment, -1000.0)
        report = self.env.ref("l10n_ca_cca.action_report_cca_schedule")
        html = report._render_qweb_html(report.report_name, schedule.ids)[0]
        self.assertIn(b"line 403", html)

    def test_short_year_zero_and_maximum(self):
        # 184-day year: 20% x 10,000 x 184 / 365 = 1,008.22.
        schedule = self._schedule(2026, generate=False, date_from=date(2026, 7, 1))
        line = self.env["l10n.ca.cca.schedule.line"].create(
            {
                "schedule_id": schedule.id,
                "class_id": self._class("8").id,
                "opening_ucc": 10000.0,
            }
        )
        empty = self.env["l10n.ca.cca.schedule.line"].create(
            {"schedule_id": schedule.id, "class_id": self._class("10").id}
        )
        schedule.action_generate()
        line = self._line(schedule, "8")
        self.assertAlmostEqual(line.proration, 184 / 365, places=5)
        self.assertAlmostEqual(line.max_cca, 1008.22)
        self.assertFalse(empty.exists() and empty.max_cca)
        with self.assertRaises(ValidationError):
            line.cca_claimed = 1008.23
        line.cca_claimed = 0.0
        self.assertAlmostEqual(line.closing_ucc, 10000.0)

    def test_ccpc_immediate_expensing_window(self):
        # The CCPC designation covered property available before 2024.
        old = self._asset("8", 5000.0, "2023-03-01")
        new = self._asset("8", 5000.0, "2026-03-01")
        self.assertTrue(old.l10n_ca_cca_immediate_expensing)
        self.assertFalse(new.l10n_ca_cca_immediate_expensing)
        self.company.l10n_ca_ccpc = False
        self.assertFalse(old._l10n_ca_cca_expensing_rate())

    def test_quebec_parameter_overrides_federal(self):
        # A Quebec rate parameter applies to the Quebec schedule only:
        # 25% x 10,000 = 2,500 against 20% x 10,000 = 2,000.
        self.env["base.time.parameter"].create(
            {
                "name": "Quebec class 8 rate",
                "code": "l10n_ca.cca.qc.class_8.rate",
                "type": "float",
                "company_id": False,
                "version_ids": [(0, 0, {"date_from": "2026-01-01", "value": "0.25"})],
            }
        )
        values = []
        for jurisdiction in ("federal", "quebec"):
            schedule = self._schedule(2026, generate=False, jurisdiction=jurisdiction)
            self.env["l10n.ca.cca.schedule.line"].create(
                {
                    "schedule_id": schedule.id,
                    "class_id": self._class("8").id,
                    "opening_ucc": 10000.0,
                }
            )
            schedule.action_generate()
            values.append(self._line(schedule, "8").max_cca)
        self.assertAlmostEqual(values[0], 2000.0)
        self.assertAlmostEqual(values[1], 2500.0)

    def test_name_in_user_language(self):
        # The stored name takes the jurisdiction label of the user's
        # language, not the English selection label.
        self.env["res.lang"]._activate_lang("fr_CA")
        self.env["ir.module.module"]._load_module_terms(["l10n_ca_cca"], ["fr_CA"])
        schedule = self.Schedule.with_context(lang="fr_CA").create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 12, 31),
            }
        )
        self.assertEqual(schedule.name, "DPA 2026 - Fédéral (annexe 8 de la T2)")
        report = self.env.ref("l10n_ca_cca.action_report_cca_schedule")
        self._asset("8", 1000.0, "2026-06-01")
        self._asset("50", 3000.0, "2026-03-01")
        schedule.action_generate()
        html = (
            report.with_context(lang="fr_CA")
            ._render_qweb_html(report.report_name, schedule.ids)[0]
            .decode()
        )
        self.assertIn(">20,00<", html)
        self.assertNotIn(">20.0<", html)
        # An expensed class shows a nil CCA base next to a full claim: the
        # expensed additions are printed under the base, with a legend.
        self.assertIn("+ passé en charges :", html)
        self.assertIn("hors de la base de la DPA", html)
