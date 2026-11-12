# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

# Salary rules of this module added to every "Canada - Base" structure, with
# their (debit, credit) accounts of the ca_2023 chart: the employer
# contributions are expenses owed to their payee, as in the federal module.
_NL_RULES = (
    "l10n_ca_nl_payroll.rule_nl_salary",
    "l10n_ca_nl_payroll.rule_nl_wcb_insurable",
    "l10n_ca_nl_payroll.rule_nl_employer_tax",
    "l10n_ca_nl_payroll.rule_nl_wcb",
)
_NL_RULE_ACCOUNTS = {
    "l10n_ca_nl_payroll.rule_nl_employer_tax": ("l10n_ca_512121", "l10n_ca_221206"),
    "l10n_ca_nl_payroll.rule_nl_wcb": ("l10n_ca_512121", "l10n_ca_221206"),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    def l10n_ca_payroll_setup(self):
        """Also add the Newfoundland and Labrador rules to the structure."""
        result = super().l10n_ca_payroll_setup()
        self._l10n_ca_payroll_add_rules(_NL_RULES, _NL_RULE_ACCOUNTS)
        return result
