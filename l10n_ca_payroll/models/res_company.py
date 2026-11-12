# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

# Salary rule -> (debit account, credit account) of the ca_2023 chart.
# Deductions are negative amounts: the debit account receives the credit,
# so the liability for the source deductions grows and the wages payable
# shrink by the same amount. Employer contributions are positive.
_CA_2023_RULE_ACCOUNTS = {
    "rule_gross": ("l10n_ca_512110", "l10n_ca_221203"),
    "rule_rpp": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_rrsp": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_union": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_support": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_lsvcc": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_cpp": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_cpp2": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_ei": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_federal_tax": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_provincial_tax": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_cpp_employer": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_cpp2_employer": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_ei_employer": ("l10n_ca_512121", "l10n_ca_221206"),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_payroll_account_number = fields.Char(
        string="Payroll Program Account",
        size=15,
        help="CRA payroll program account (business number followed by "
        "RP and four digits), printed on the T4 slips and the remittance "
        "vouchers.",
    )
    l10n_ca_ei_employer_multiplier = fields.Float(
        string="Reduced EI Employer Multiplier",
        digits=(4, 3),
        help="Multiplier of the employee EI premium assigned to the "
        "employer under the EI Premium Reduction Program. Leave 0 to use "
        "the legal multiplier of the time parameter "
        "l10n_ca.ei.employer_multiplier.",
    )

    def _l10n_ca_payroll_structure(self):
        """Return the "Canada - Base" structure of this company.

        The structure shipped in data belongs to the main company; another
        company receives a copy that shares the same salary rules. The
        template is read as superuser: the multi-company rule of the
        structures hides it from the users of the other companies.
        """
        self.ensure_one()
        template = self.env.ref(
            "l10n_ca_payroll.structure_ca_base", raise_if_not_found=False
        )
        if not template:
            return self.env["hr.payroll.structure"]
        template = template.sudo()
        if template.company_id == self:
            return template.with_env(self.env)
        structure = self.env["hr.payroll.structure"].search(
            [("code", "=", template.code), ("company_id", "=", self.id)], limit=1
        )
        if not structure:
            # copy() of hr.payroll.structure forces a "(copy)" suffix on the
            # code, which is the key of the search above.
            structure = template.copy({"company_id": self.id})
            structure.write({"code": template.code, "name": template.name})
        return structure.with_env(self.env)

    def l10n_ca_payroll_apply_default_accounts(self):
        """Propose the ca_2023 accounts on the statutory salary rules."""
        return self._l10n_ca_payroll_apply_rule_accounts(
            {
                f"l10n_ca_payroll.{xmlid}": codes
                for xmlid, codes in _CA_2023_RULE_ACCOUNTS.items()
            }
        )

    def _l10n_ca_payroll_apply_rule_accounts(self, accounts):
        """Propose ca_2023 accounts on salary rules.

        ``accounts`` maps the full XML id of a rule to the XML ids (without
        module) of its debit and credit accounts in the ca_2023 chart.
        Accounts are company-dependent on the rules: each company gets its
        own. A rule that already has an account for the company keeps it.
        Companies whose chart is not ca_2023 are left untouched.
        """
        Rule = self.env["hr.salary.rule"]
        for company in self.filtered(lambda c: c.chart_template == "ca_2023"):
            chart = self.env["account.chart.template"].with_company(company)
            for rule_xmlid, codes in accounts.items():
                rule = self.env.ref(rule_xmlid, raise_if_not_found=False)
                if not rule:
                    continue
                rule = Rule.browse(rule.id).with_company(company)
                vals = {}
                for field_name, xmlid in zip(
                    ("account_debit", "account_credit"), codes, strict=True
                ):
                    account = chart.ref(xmlid, raise_if_not_found=False)
                    if account and not rule[field_name]:
                        vals[field_name] = account.id
                if vals:
                    rule.write(vals)
        return True

    def _l10n_ca_payroll_add_rules(self, rule_xmlids, accounts=None):
        """Add salary rules to the "Canada - Base" structure of each company.

        ``rule_xmlids`` are full XML ids; ``accounts`` is the mapping of
        ``_l10n_ca_payroll_apply_rule_accounts``. A province module calls it
        from ``l10n_ca_payroll_setup``; a second call adds nothing.
        """
        rules = self.env["hr.salary.rule"]
        for xmlid in rule_xmlids:
            rules |= self.env.ref(xmlid)
        for company in self:
            structure = company._l10n_ca_payroll_structure().sudo()
            missing = rules - structure.rule_ids
            if missing:
                structure.write({"rule_ids": [(4, rule.id) for rule in missing]})
        if accounts:
            self._l10n_ca_payroll_apply_rule_accounts(accounts)
        return True

    def l10n_ca_payroll_setup(self):
        """Give the company its Canadian structure and default accounts."""
        for company in self:
            structure = company._l10n_ca_payroll_structure()
            if structure and not company.payroll_structure_id:
                company.payroll_structure_id = structure
        self.l10n_ca_payroll_apply_default_accounts()
        return True
