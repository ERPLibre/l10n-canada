# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

# Salary rules of this module added to every "Canada - Base" structure, with
# their (debit, credit) accounts of the ca_2023 chart. The payroll tax is a
# deduction, a negative amount, booked like the federal source deductions:
# it moves from the wages payable to the liability owed to its payee. The
# WSCC assessment is an employer expense owed to its payee.
_NT_RULES = (
    "l10n_ca_nt_payroll.rule_nt_salary",
    "l10n_ca_nt_payroll.rule_nt_wcb_insurable",
    "l10n_ca_nt_payroll.rule_nt_payroll_tax",
    "l10n_ca_nt_payroll.rule_nt_wcb",
)
_NT_RULE_ACCOUNTS = {
    "l10n_ca_nt_payroll.rule_nt_payroll_tax": ("l10n_ca_221206", "l10n_ca_221203"),
    "l10n_ca_nt_payroll.rule_nt_wcb": ("l10n_ca_512121", "l10n_ca_221206"),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    def l10n_ca_payroll_setup(self):
        """Also add the Northwest Territories rules to the structure."""
        result = super().l10n_ca_payroll_setup()
        self._l10n_ca_payroll_add_rules(_NT_RULES, _NT_RULE_ACCOUNTS)
        return result
