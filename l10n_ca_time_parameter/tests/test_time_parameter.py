# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..tools import bracket_constant, marginal_rate, progressive_tax


@tagged("post_install", "-at_install")
class TestTimeParameter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Parameter = cls.env["base.time.parameter"]

    def _make(self, code, versions, ptype="float", company=False):
        return self.Parameter.create(
            {
                "name": code,
                "code": code,
                "type": ptype,
                "company_id": company and company.id,
                "version_ids": [
                    (0, 0, {"date_from": d, "value": v}) for d, v in versions
                ],
            }
        )

    def test_value_at_date(self):
        self._make("l10n_ca.test.rate", [("2025-01-01", "0.15"), ("2026-01-01", "0.14")])
        param = self.company._l10n_ca_param
        self.assertEqual(param("l10n_ca.test.rate", date(2025, 6, 30)), 0.15)
        self.assertEqual(param("l10n_ca.test.rate", date(2026, 1, 1)), 0.14)

    def test_zero_is_a_value(self):
        self._make("l10n_ca.test.zero", [("2025-01-01", "0")])
        self.assertEqual(
            self.company._l10n_ca_param("l10n_ca.test.zero", date(2026, 1, 1)), 0.0
        )

    def test_company_wins_over_global(self):
        self._make("l10n_ca.test.both", [("2025-01-01", "1")])
        self._make("l10n_ca.test.both", [("2025-01-01", "2")], company=self.company)
        self.assertEqual(
            self.company._l10n_ca_param("l10n_ca.test.both", date(2026, 1, 1)), 2.0
        )

    def test_missing_raises_or_defaults(self):
        self._make("l10n_ca.test.late", [("2027-01-01", "1")])
        with self.assertRaises(UserError):
            self.company._l10n_ca_param("l10n_ca.test.late", date(2026, 1, 1))
        self.assertIsNone(
            self.company._l10n_ca_param(
                "l10n_ca.test.late", date(2026, 1, 1), default=None
            )
        )

    def test_json_brackets(self):
        self._make(
            "l10n_ca.test.brackets",
            [("2026-01-01", "[[0, 0.1], [100, 0.2]]")],
            ptype="json",
        )
        table = self.company._l10n_ca_param("l10n_ca.test.brackets", date(2026, 5, 1))
        self.assertAlmostEqual(progressive_tax(150, table), 20.0)

    def test_global_parameter_visible_to_manager(self):
        self._make("l10n_ca.test.visible", [("2025-01-01", "1")])
        user = self.env["res.users"].create(
            {
                "name": "Canadian accountant",
                "login": "l10n_ca_tp_manager",
                "group_ids": [(6, 0, [self.env.ref("account.group_account_manager").id])],
            }
            if "group_ids" in self.env["res.users"]._fields
            else {
                "name": "Canadian accountant",
                "login": "l10n_ca_tp_manager",
                "groups_id": [(6, 0, [self.env.ref("account.group_account_manager").id])],
            }
        )
        found = self.Parameter.with_user(user).search(
            [("code", "=", "l10n_ca.test.visible")]
        )
        self.assertEqual(len(found), 1)


class TestBracketTools(TransactionCase):
    def test_progressive_tax(self):
        table = [[0, 0.1], [100, 0.2], [200, 0.3]]
        self.assertEqual(progressive_tax(-5, table), 0.0)
        self.assertAlmostEqual(progressive_tax(50, table), 5.0)
        self.assertAlmostEqual(progressive_tax(250, table), 10 + 20 + 15)
        self.assertEqual(marginal_rate(250, table), 0.3)
        self.assertAlmostEqual(
            marginal_rate(250, table) * 250 - bracket_constant(250, table),
            progressive_tax(250, table),
        )

    def test_table_must_start_at_zero(self):
        with self.assertRaises(ValueError):
            progressive_tax(10, [[5, 0.1]])
