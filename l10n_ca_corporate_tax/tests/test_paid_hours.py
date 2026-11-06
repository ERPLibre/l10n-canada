# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.tests import tagged

from .common import L10nCaCorporateTaxCommon


@tagged("post_install", "-at_install")
class TestPaidHours(L10nCaCorporateTaxCommon):
    def _record(self, year, hours, **values):
        values.update(
            company_id=self.company.id,
            date_from=date(year, 1, 1),
            date_to=date(year, 12, 31),
            line_ids=[(0, 0, {"name": "Employee", "hours": h}) for h in hours],
        )
        return self.env["l10n.ca.paid.hours"].create(values)

    def test_factor_thresholds(self):
        # Shipped thresholds: 5,000 and 5,500 hours. Factor =
        # (hours - 5,000) / 500, between 0 and 1.
        record = self._record(2026, [4800.0])
        self.assertEqual(record.sbd_factor, 0.0)
        record.line_ids.hours = 5250.0
        self.assertAlmostEqual(record.sbd_factor, 0.5)  # 250 / 500
        record.line_ids.hours = 5600.0
        self.assertEqual(record.sbd_factor, 1.0)
        record.line_ids.hours = 5000.0
        self.assertEqual(record.sbd_factor, 0.0)
        record.line_ids.hours = 5500.0
        self.assertEqual(record.sbd_factor, 1.0)

    def test_preceding_year_with_associated_corporations(self):
        # 2025: 3,000 own + 2,600 associated = 5,600 hours, more than the
        # 4,800 of 2026, so 2026 gets the full factor.
        self._record(2025, [3000.0], associated_hours=2600.0)
        current = self._record(2026, [4800.0], associated_hours=9000.0)
        self.assertAlmostEqual(current.own_hours, 4800.0)
        self.assertAlmostEqual(current.previous_group_hours, 5600.0)
        self.assertAlmostEqual(current.retained_hours, 5600.0)
        self.assertEqual(current.sbd_factor, 1.0)

    def test_associated_hours_do_not_count_in_current_year(self):
        current = self._record(2026, [4800.0], associated_hours=9000.0)
        self.assertEqual(current.sbd_factor, 0.0)

    def test_weekly_cap_and_sector(self):
        record = self._record(2026, [])
        record.line_ids = [(0, 0, {"name": "Overtime", "hours": 2500.0, "weeks": 50.0})]
        # 40 hours x 50 weeks = 2,000 counted hours.
        self.assertAlmostEqual(record.own_hours, 2000.0)
        record.primary_manufacturing_ratio = 37.5
        # (0.375 - 0.25) / (0.50 - 0.25) = 0.5
        self.assertAlmostEqual(record.sbd_factor, 0.5)
        record.sector_exempt = True
        self.assertEqual(record.sbd_factor, 1.0)

    def test_majority_shareholder_factor(self):
        # CO-771 notes 2 and 3: 1.1 x the hours worked by the majority
        # shareholder. 3,000 + 1.1 x 2,000 = 5,200 hours: (5,200 - 5,000) /
        # 500 = 0.4.
        record = self._record(2026, [3000.0])
        record.line_ids = [
            (0, 0, {"name": "Owner", "source": "shareholder", "hours": 2000.0})
        ]
        shareholder = record.line_ids.filtered(
            lambda line: line.source == "shareholder"
        )
        self.assertAlmostEqual(shareholder.counted_hours, 2200.0)
        self.assertAlmostEqual(record.own_hours, 5200.0)
        self.assertAlmostEqual(record.sbd_factor, 0.4)
        # The weekly cap applies to the hours worked: min(2,500, 40 x 50)
        # = 2,000, x 1.1 = 2,200.
        shareholder.write({"hours": 2500.0, "weeks": 50.0})
        self.assertAlmostEqual(shareholder.counted_hours, 2200.0)
        shareholder.source = "employee"
        self.assertAlmostEqual(shareholder.counted_hours, 2000.0)

    def test_short_year_annualized(self):
        # 2026-04-01 to 2026-12-31: 275 days. 4,500 x 365 / 275 = 5,972.73
        # hours, above 5,500: full factor. The same hours over a full year
        # give nil.
        short = self.env["l10n.ca.paid.hours"].create(
            {
                "company_id": self.company.id,
                "date_from": date(2026, 4, 1),
                "date_to": date(2026, 12, 31),
                "line_ids": [(0, 0, {"name": "Employee", "hours": 4500.0})],
            }
        )
        self.assertAlmostEqual(short.own_hours, 4500.0)
        self.assertAlmostEqual(short.own_hours_annualized, 4500.0 * 365 / 275)
        self.assertEqual(short.sbd_factor, 1.0)
        full = self._record(2027, [4500.0])
        self.assertAlmostEqual(full.own_hours_annualized, 4500.0)
        self.assertEqual(full.sbd_factor, 0.0)

    def test_short_preceding_year_not_annualized(self):
        # Preceding year 2025-07-01 to 2025-12-31 (184 days): 3,000 own +
        # 2,000 associated = 5,000 hours, kept as is (annualized they
        # would exceed 5,500): factor nil.
        self.env["l10n.ca.paid.hours"].create(
            {
                "company_id": self.company.id,
                "date_from": date(2025, 7, 1),
                "date_to": date(2025, 12, 31),
                "associated_hours": 2000.0,
                "line_ids": [(0, 0, {"name": "Employee", "hours": 3000.0})],
            }
        )
        current = self._record(2026, [1000.0])
        self.assertAlmostEqual(current.previous_group_hours, 5000.0)
        self.assertAlmostEqual(current.retained_hours, 5000.0)
        self.assertEqual(current.sbd_factor, 0.0)

    def test_hook(self):
        self._record(2026, [1000.0, 1500.0])
        self.assertAlmostEqual(
            self.company._l10n_ca_get_paid_hours(date(2026, 1, 1), date(2026, 12, 31)),
            2500.0,
        )
