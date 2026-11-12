# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Weekly check of the official pages, without network.

``_l10n_ca_fetch`` is replaced by pages built like the official ones: the
CRA tables by year, the indexation table by column and the T4127 list of
editions. The date is November 15, 2026, so the years checked are 2026 and
2027.
"""

from unittest.mock import patch

import requests
from freezegun import freeze_time

from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_ca_payroll.tools import watch


def _cpp_page(rows):
    body = "".join(
        f"<tr><td>{year}</td><td>${ympe}</td><td>$3,500</td><td>$0</td>"
        f"<td>{rate}</td><td>$0</td><td>$0</td></tr>"
        for year, ympe, rate in rows
    )
    return (
        '<html><body><table id="ajax-cpprate-tbl"><caption>CPP contribution '
        "rates, maximums and exemptions all years</caption><tr><th>Year</th>"
        f"<th>YMPE</th></tr>{body}</table></body></html>"
    ).encode()


T4127_2026 = (
    b"<html><body><a>Payroll Deductions Formulas - 123rd Edition - Effective "
    b"July 1, 2026</a><a>Payroll Deductions Formulas - 122nd Edition - "
    b"Effective January 1, 2026</a></body></html>"
)
T4127_2027 = T4127_2026.replace(
    b"<body>",
    b"<body><a>Payroll Deductions Formulas - 124th Edition - Effective "
    b"January 1, 2027</a>",
)


@tagged("post_install", "-at_install")
@freeze_time("2026-11-15")
class TestSourceWatch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Payroll Watch Manager",
                "login": "payroll_watch_manager",
                "groups_id": [
                    (6, 0, [cls.env.ref("payroll.group_payroll_manager").id])
                ],
            }
        )
        cls.cpp = cls.env.ref("l10n_ca_payroll.source_cra_cpp_rates")
        cls.t4127 = cls.env.ref("l10n_ca_payroll.source_t4127_jan_2026")
        cls.Source = type(cls.env["l10n_ca.payroll.source"])

    def _check(self, source, page, status=200):
        def fetch(self_, url, probe=False):
            if isinstance(page, Exception):
                raise page
            return status, page

        with patch.object(self.Source, "_l10n_ca_fetch", fetch):
            source.action_l10n_ca_watch()

    def _todo(self, source):
        todo = self.env.ref("mail.mail_activity_data_todo")
        return source.activity_ids.filtered(lambda a: a.activity_type_id == todo)

    def test_figures_that_match(self):
        # 2027 YMPE 76,700 and rate 5.75%, 2026 74,600 and 5.95%: the
        # versions shipped with the module.
        page = _cpp_page([("New 2027", "76,700", "5.75"), ("2026", "74,600", "5.95")])
        self._check(self.cpp, page)
        self.assertEqual(self.cpp.watch_state, "ok")
        self.assertIn("l10n_ca.cpp.ympe = 76700.0: matches.", self.cpp.watch_message)
        self.assertFalse(self._todo(self.cpp))

    def test_figure_that_differs_schedules_an_activity(self):
        page = _cpp_page([("New 2027", "77,000", "5.75"), ("2026", "74,600", "5.95")])
        self._check(self.cpp, page)
        self.assertEqual(self.cpp.watch_state, "differs")
        self.assertIn(
            "gives 77000.0, the 2027 version holds 76700", self.cpp.watch_message
        )
        activity = self._todo(self.cpp)
        self.assertEqual(len(activity), 1)
        self.assertEqual(
            activity.user_id,
            self.env["res.users"].search(
                [
                    (
                        "groups_id",
                        "in",
                        self.env.ref("payroll.group_payroll_manager").id,
                    ),
                    ("share", "=", False),
                ],
                order="id",
                limit=1,
            ),
        )
        # The same finding the next week adds no second activity.
        self._check(self.cpp, page)
        self.assertEqual(len(self._todo(self.cpp)), 1)

    def test_next_year_not_yet_published(self):
        self._check(self.cpp, _cpp_page([("2026", "74,600", "5.95")]))
        self.assertEqual(self.cpp.watch_state, "pending")
        self.assertIn("2027: not yet published.", self.cpp.watch_message)

    def test_changed_page_is_reported(self):
        self._check(
            self.cpp,
            b"<html><body><table><caption>Other</caption></table></body></html>",
        )
        self.assertEqual(self.cpp.watch_state, "changed")
        self.assertIn("no longer has the expected content", self.cpp.watch_message)
        self.assertTrue(self._todo(self.cpp))
        self._check(self.cpp, b"", status=404)
        self.assertEqual(self.cpp.watch_state, "changed")
        self.assertIn("HTTP 404", self.cpp.watch_message)

    def test_unreachable_page_is_reported(self):
        self._check(self.cpp, requests.ConnectionError("no route"))
        self.assertEqual(self.cpp.watch_state, "error")
        self.assertIn("did not answer", self.cpp.watch_message)

    def test_publication_reviewed(self):
        self._check(self.t4127, T4127_2026)
        self.assertEqual(self.t4127.watch_state, "pending")
        self._check(self.t4127, T4127_2027)
        self.assertEqual(self.t4127.watch_state, "published")
        self.assertTrue(self._todo(self.t4127))

        def fetch(self_, url, probe=False):
            return 200, T4127_2027

        with patch.object(self.Source, "_l10n_ca_fetch", fetch):
            self.t4127.action_l10n_ca_watch_acknowledge()
        self.assertEqual(self.t4127.watch_acknowledged_year, 2027)
        self.assertEqual(self.t4127.watch_state, "ok")
        self.assertFalse(self._todo(self.t4127))

    def test_indexation_column_of_the_next_year(self):
        source = self.env.ref("l10n_ca_payroll.source_cra_indexation")
        page = (
            b"<html><body><table><caption>Tax bracket thresholds</caption>"
            b"<tr><th>Description</th><th>2027</th><th>2026</th></tr>"
            b"<tr><td>Taxable income above which the 20.5% bracket begins</td>"
            b"<td>$60,000</td><td>$58,523</td></tr>"
            b"<tr><td>Taxable income above which the 26% bracket begins</td>"
            b"<td>$120,000</td><td>$117,045</td></tr>"
            b"<tr><td>Taxable income above which the 29% bracket begins</td>"
            b"<td>$186,000</td><td>$181,440</td></tr>"
            b"<tr><td>Taxable income above which the 33% bracket begins</td>"
            b"<td>$265,000</td><td>$258,482</td></tr></table>"
            b"<table><caption>Amounts relating to non-refundable tax credits</caption>"
            b"<tr><th>Description</th><th>2027</th><th>2026</th></tr>"
            b"<tr><td>Basic personal amount for individuals whose net income for "
            b"the year is greater than or equal to the amount</td><td>$15,200</td>"
            b"<td>$14,829</td></tr><tr><td>Basic personal amount (maximum) for "
            b"individuals</td><td>$16,800</td><td>$16,452</td></tr>"
            b"<tr><td>Canada employment amount (maximum)</td><td>$1,530</td>"
            b"<td>$1,501</td></tr></table></body></html>"
        )
        self._check(source, page)
        # 2026 matches the shipped versions; the 2027 figures have none.
        self.assertEqual(source.watch_state, "published")
        self.assertIn(
            "l10n_ca.federal.bpa_max = 16452.0: matches.", source.watch_message
        )
        self.assertIn(
            "l10n_ca.federal.bpa_max: 16800.0 published for 2027, no version yet.",
            source.watch_message,
        )

    def test_cron_survives_a_failing_watcher(self):
        def fetch(self_, url, probe=False):
            raise ValueError("unexpected")

        logger = "odoo.addons.l10n_ca_payroll.models.l10n_ca_payroll_source_watch"
        with (
            patch.object(self.Source, "_l10n_ca_fetch", fetch),
            self.assertLogs(logger, level="ERROR") as logs,
        ):
            self.env["l10n_ca.payroll.source"]._cron_l10n_ca_watch()
        self.assertIn("Official source watch failed", logs.output[0])

    def test_extractors_reject_numbers_they_cannot_read(self):
        with self.assertRaises(watch.PageChanged):
            watch.amount("n/a")
        self.assertEqual(watch.amount("2 032,99 $", decimal_comma=True), 2032.99)
        self.assertEqual(watch.rate("0,430 %", decimal_comma=True), 0.0043)
