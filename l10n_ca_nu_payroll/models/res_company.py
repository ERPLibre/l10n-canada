# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

# Salary rules of this module added to every "Canada - Base" structure, with
# their (debit, credit) accounts of the ca_2023 chart. The payroll tax is a
# deduction, a negative amount, booked like the federal source deductions:
# it moves from the wages payable to the liability owed to its payee. The
# WSCC assessment is an employer expense owed to its payee.
_NU_RULES = (
    "l10n_ca_nu_payroll.rule_nu_salary",
    "l10n_ca_nu_payroll.rule_nu_wcb_insurable",
    "l10n_ca_nu_payroll.rule_nu_payroll_tax",
    "l10n_ca_nu_payroll.rule_nu_wcb",
)
_NU_RULE_ACCOUNTS = {
    "l10n_ca_nu_payroll.rule_nu_payroll_tax": ("l10n_ca_221206", "l10n_ca_221203"),
    "l10n_ca_nu_payroll.rule_nu_wcb": ("l10n_ca_512121", "l10n_ca_221206"),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    def l10n_ca_payroll_setup(self):
        """Also add the Nunavut rules to the structure."""
        result = super().l10n_ca_payroll_setup()
        self._l10n_ca_payroll_add_rules(_NU_RULES, _NU_RULE_ACCOUNTS)
        return result
