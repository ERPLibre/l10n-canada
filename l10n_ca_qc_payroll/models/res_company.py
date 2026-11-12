# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

from ..tools import hsf_rate

# Salary rule -> (debit account, credit account) of the ca_2023 chart, same
# convention as the federal rules: the employee premium is a negative
# deduction, the employer contributions are positive expenses.
_CA_2023_QC_RULE_ACCOUNTS = {
    "rule_qpip": ("l10n_ca_221206", "l10n_ca_221203"),
    "rule_qpip_employer": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_hsf": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_cnt": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_wsdrf": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_cnesst": ("l10n_ca_512121", "l10n_ca_221206"),
}

# Rules added to every "Canada - Base" structure.
_QC_RULES = (
    "rule_qc_salary",
    "rule_qpip",
    "rule_qpip_employer",
    "rule_hsf",
    "rule_cnt",
    "rule_wsdrf",
    "rule_cnesst",
)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_qc_rq_account_number = fields.Char(
        string="Revenu Quebec Identification Number",
        size=16,
        help="Identification number of the source deductions file at "
        "Revenu Quebec (ten digits followed by RS and four digits), printed "
        "on the RL-1 slips and the RL-1 summary.",
    )
    l10n_ca_qc_remitter_type = fields.Selection(default="monthly")
    l10n_ca_qc_hsf_sector = fields.Selection(
        [
            ("general", "General (all other employers)"),
            ("primary_manufacturing", "Primary and manufacturing sectors"),
            ("public", "Public sector"),
        ],
        string="Health Services Fund Sector",
        default="general",
        required=True,
        help="Primary and manufacturing: more than 50% of the total payroll "
        "is attributable to activities of NAICS codes 11, 21 and 31 to 33. "
        "The sector selects the rate formula of the time parameter "
        "l10n_ca.qc.hsf.formula.",
    )
    l10n_ca_qc_hsf_basis = fields.Selection(
        [
            ("estimate", "Total payroll of the previous year"),
            ("year_to_date", "Total payroll paid since January 1 (new employer)"),
        ],
        string="Health Services Fund Rate Basis",
        default="estimate",
        required=True,
        help="Total payroll used for the rate of the periodic HSF payments. "
        "An employer in its first two years of contributions uses the "
        "payroll paid from January 1 to the end of the remittance period, "
        "associated employers included, and each remittance applies the "
        "rate of its period; the others use the total payroll of the "
        "previous year. The RL-1 summary recomputes the rate from the "
        "actual total payroll.",
    )
    l10n_ca_qc_lump_sum_method = fields.Selection(
        [
            ("1", "Method 1: income of the year to date"),
            ("2", "Method 2: annualized pay"),
        ],
        string="Quebec Tax Method for Lump Sums",
        default="2",
        required=True,
        help="Method of TP-1015.F section 2.1.2 for the Quebec tax on "
        "bonuses, retroactive pay and similar lump-sum payments. Method 1 "
        "taxes the payment at the brackets of the income earned since "
        "January 1 plus the pays left in the year, and spreads a payment "
        "that crosses a bracket over both rates; method 2 applies the rate "
        "of the bracket of the annualized pay to the whole payment. Both "
        "withhold the flat rate when the annual salary and the lump sums "
        "total at most the basic personal amount.",
    )
    l10n_ca_qc_total_payroll_estimate = fields.Monetary(
        string="Previous Year Total Payroll",
        help="Total payroll of the previous year, including the employers "
        "associated with the company on December 31 and the remuneration "
        "paid outside Quebec. It sets the estimated Health Services Fund "
        "rate.",
    )
    l10n_ca_qc_wsdrf_payroll_estimate = fields.Monetary(
        string="Previous Year Payroll (WSDRF)",
        help="Remuneration of the previous year paid by the company alone "
        "and subject to the WSDRF contribution (line 51 of the RL-1 "
        "summary), without the associated employers nor the remuneration "
        "paid outside Quebec. Above the threshold of the time parameter "
        "l10n_ca.qc.wsdrf.payroll_threshold, the payslips accrue the WSDRF "
        "contribution. With the new employer basis, the remuneration paid "
        "since January 1 is used instead.",
    )
    l10n_ca_qc_associated_payroll = fields.Monetary(
        string="Payroll of Associated Employers",
        help="Remuneration paid since January 1 of the current year by the "
        "employers associated with the company on December 31. It is added "
        "to the payroll of the company to determine the Health Services "
        "Fund rate: of the periodic payments with the new employer basis, "
        "which requires updating it each remittance period, and of the "
        "RL-1 summary (line 50.1), where it is the amount of the whole "
        "year.",
    )
    l10n_ca_qc_cnesst_rate = fields.Float(
        string="CNESST Rate per $100",
        digits=(6, 4),
        help="Rate per $100 of insurable payroll set by the CNESST "
        "classification decision of the year (or the letter announcing a "
        "new rate). Leave 0 when the company has no CNESST coverage.",
    )
    l10n_ca_qc_cnt_exempt = fields.Boolean(
        string="Not Subject to the Labour Standards Contribution",
        help="Religious institutions, charities helping persons in need "
        "free of charge, businesses governed by the Canada Labour Code and "
        "international organizations do not pay the contribution related "
        "to labour standards.",
    )

    # ------------------------------------------------------------------
    # Rates
    # ------------------------------------------------------------------

    def _l10n_ca_qc_hsf_rate(self, total_payroll, date):
        """Return the Health Services Fund rate, in percent, at ``date``."""
        self.ensure_one()
        param = self._l10n_ca_param
        formula = param("l10n_ca.qc.hsf.formula", date)[self.l10n_ca_qc_hsf_sector]
        return hsf_rate(
            total_payroll,
            formula,
            param("l10n_ca.qc.hsf.payroll_min", date),
            param("l10n_ca.qc.hsf.payroll_max", date),
        )

    # ------------------------------------------------------------------
    # Set-up
    # ------------------------------------------------------------------

    def l10n_ca_payroll_setup(self):
        """Also add the Quebec rules to the structure and propose accounts."""
        result = super().l10n_ca_payroll_setup()
        rules = self.env["hr.salary.rule"]
        for xmlid in _QC_RULES:
            rules |= self.env.ref(f"l10n_ca_qc_payroll.{xmlid}")
        for company in self:
            structure = company._l10n_ca_payroll_structure().sudo()
            missing = rules - structure.rule_ids
            if missing:
                structure.write({"rule_ids": [(4, rule.id) for rule in missing]})
        self._l10n_ca_qc_apply_default_accounts()
        return result

    def _l10n_ca_qc_apply_default_accounts(self):
        """Propose the ca_2023 accounts on the Quebec salary rules.

        Same rule as the federal module: accounts are company-dependent, an
        account already set is kept and other charts are left untouched.
        """
        Rule = self.env["hr.salary.rule"]
        for company in self.filtered(lambda c: c.chart_template == "ca_2023"):
            chart = self.env["account.chart.template"].with_company(company)
            for xmlid, codes in _CA_2023_QC_RULE_ACCOUNTS.items():
                rule = Rule.browse(
                    self.env.ref(f"l10n_ca_qc_payroll.{xmlid}").id
                ).with_company(company)
                vals = {}
                for field_name, account_xmlid in zip(
                    ("account_debit", "account_credit"), codes, strict=True
                ):
                    account = chart.ref(account_xmlid, raise_if_not_found=False)
                    if account and not rule[field_name]:
                        vals[field_name] = account.id
                if vals:
                    rule.write(vals)
