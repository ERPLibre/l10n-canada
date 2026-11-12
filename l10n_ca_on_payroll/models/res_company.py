# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

# Salary rules of this module added to every "Canada - Base" structure, with
# their (debit, credit) accounts of the ca_2023 chart: the employer
# contributions are expenses owed to their payee, as in the federal module.
_ON_RULES = (
    "l10n_ca_on_payroll.rule_on_salary",
    "l10n_ca_on_payroll.rule_on_wsib_insurable",
    "l10n_ca_on_payroll.rule_on_eht",
    "l10n_ca_on_payroll.rule_on_wsib",
)
_ON_RULE_ACCOUNTS = {
    "l10n_ca_on_payroll.rule_on_eht": ("l10n_ca_512121", "l10n_ca_221206"),
    "l10n_ca_on_payroll.rule_on_wsib": ("l10n_ca_512121", "l10n_ca_221206"),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    def l10n_ca_payroll_setup(self):
        """Also add the Ontario rules to the structure and propose accounts."""
        result = super().l10n_ca_payroll_setup()
        self._l10n_ca_payroll_add_rules(_ON_RULES, _ON_RULE_ACCOUNTS)
        return result
