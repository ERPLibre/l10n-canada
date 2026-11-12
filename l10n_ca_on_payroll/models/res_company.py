# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

from odoo.addons.l10n_ca_time_parameter.tools import marginal_rate

# Salary rule -> (debit account, credit account) of the ca_2023 chart, same
# convention as the federal rules: the employer contributions are positive
# expenses owed to their payee.
_CA_2023_ON_RULE_ACCOUNTS = {
    "rule_on_eht": ("l10n_ca_512121", "l10n_ca_221206"),
    "rule_on_wsib": ("l10n_ca_512121", "l10n_ca_221206"),
}

# Rules added to every "Canada - Base" structure.
_ON_RULES = (
    "rule_on_salary",
    "rule_on_wsib_insurable",
    "rule_on_eht",
    "rule_on_wsib",
)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_on_eht_account_number = fields.Char(
        string="EHT Account Number",
        help="Employer Health Tax account number given by the Ontario "
        "Ministry of Finance.",
    )
    l10n_ca_on_eht_eligible = fields.Boolean(
        string="Eligible Employer (EHT Exemption)",
        default=True,
        help="Eligible employers deduct the EHT exemption from their total "
        "Ontario remuneration. Public-sector employers, federal and other "
        "provincial Crown bodies and the other persons excluded by the "
        "Employer Health Tax Act are not eligible: they pay the tax on "
        "their whole Ontario remuneration.",
    )
    l10n_ca_on_eht_charity = fields.Boolean(
        string="Registered Charity (EHT)",
        help="A registered charity keeps its EHT exemption whatever its "
        "total Ontario remuneration.",
    )
    l10n_ca_on_eht_associated = fields.Boolean(
        string="Associated Employer (EHT)",
        help="The company belongs to a group of associated employers that "
        "shares one EHT exemption by an allocation agreement delivered by "
        "March 15 of the following year.",
    )
    l10n_ca_on_eht_allocated_exemption = fields.Monetary(
        string="EHT Exemption Allocated to the Company",
        help="Share of the group exemption allocated to the company by the "
        "agreement of the associated employers. The company takes the "
        "lesser of this amount and the exemption of the year. Enter 0 when "
        "the group allocates nothing to the company or when the total "
        "Ontario remuneration of the group exceeds the exemption "
        "threshold.",
    )
    l10n_ca_on_eht_basis = fields.Selection(
        [
            ("previous_year", "Total Ontario remuneration of the previous year"),
            ("estimate", "Estimated total Ontario remuneration of the year"),
        ],
        string="EHT Rate Basis",
        default="previous_year",
        required=True,
        help="Annual total Ontario remuneration that selects the EHT rate "
        "and, for an employer not associated, decides whether the exemption "
        "applies. The tax of the year is set on the actual remuneration by "
        "the annual return; a new employer or one whose payroll changes "
        "enters an estimate of the current year.",
    )
    l10n_ca_on_eht_previous_payroll = fields.Monetary(
        string="Previous Year Total Ontario Remuneration",
        help="Total Ontario remuneration paid by the company in the "
        "previous year, all accounts combined, before the exemption.",
    )
    l10n_ca_on_eht_estimated_payroll = fields.Monetary(
        string="Estimated Total Ontario Remuneration",
        help="Total Ontario remuneration the company expects to pay in the "
        "current year, all accounts combined, before the exemption.",
    )
    l10n_ca_on_wsib_account_number = fields.Char(
        string="WSIB Account Number",
        help="Firm or account number of the company at the WSIB.",
    )
    l10n_ca_on_wsib_rate = fields.Float(
        string="WSIB Premium Rate per $100",
        digits=(6, 4),
        help="Premium rate per $100 of insurable earnings of the annual "
        "rate notice of the WSIB for the classification of the company. "
        "Leave 0 when the company has no WSIB account (Schedule 2 "
        "employers pay the cost of their claims instead).",
    )

    # ------------------------------------------------------------------
    # Employer Health Tax
    # ------------------------------------------------------------------

    def _l10n_ca_on_eht_payroll(self):
        """Return the annual total Ontario remuneration of the rate basis."""
        self.ensure_one()
        if self.l10n_ca_on_eht_basis == "estimate":
            return self.l10n_ca_on_eht_estimated_payroll
        return self.l10n_ca_on_eht_previous_payroll

    def _l10n_ca_on_eht_rate(self, total_payroll, date):
        """Return the EHT rate of a total Ontario remuneration at ``date``.

        The rate of the last threshold that ``total_payroll`` exceeds: a
        remuneration equal to a threshold stays at the lower rate.
        """
        self.ensure_one()
        rates = self._l10n_ca_param("l10n_ca.on.eht.rates", date)
        return marginal_rate(max(total_payroll or 0.0, 0.0), rates)

    def _l10n_ca_on_eht_exemption(self, total_payroll, date):
        """Return the EHT exemption of the year of ``date``.

        0 for an employer that is not eligible. An associated employer
        takes the lesser of its allocated share and the exemption of the
        year. Another eligible employer takes the exemption of the year when
        ``total_payroll`` is at most the exemption threshold or when it is a
        registered charity, else 0. The exemption is not prorated for a
        year with a permanent establishment in Ontario during only part of
        it.
        """
        self.ensure_one()
        if not self.l10n_ca_on_eht_eligible:
            return 0.0
        param = self._l10n_ca_param
        exemption = param("l10n_ca.on.eht.exemption", date)
        if self.l10n_ca_on_eht_associated:
            return max(0.0, min(self.l10n_ca_on_eht_allocated_exemption, exemption))
        threshold = param("l10n_ca.on.eht.exemption_threshold", date)
        if self.l10n_ca_on_eht_charity or total_payroll <= threshold:
            return exemption
        return 0.0

    # ------------------------------------------------------------------
    # Set-up
    # ------------------------------------------------------------------

    def l10n_ca_payroll_setup(self):
        """Also add the Ontario rules to the structure and propose accounts."""
        result = super().l10n_ca_payroll_setup()
        rules = self.env["hr.salary.rule"]
        for xmlid in _ON_RULES:
            rules |= self.env.ref(f"l10n_ca_on_payroll.{xmlid}")
        for company in self:
            structure = company._l10n_ca_payroll_structure().sudo()
            missing = rules - structure.rule_ids
            if missing:
                structure.write({"rule_ids": [(4, rule.id) for rule in missing]})
        self._l10n_ca_on_apply_default_accounts()
        return result

    def _l10n_ca_on_apply_default_accounts(self):
        """Propose the ca_2023 accounts on the Ontario salary rules.

        Same rule as the federal module: accounts are company-dependent, an
        account already set is kept and other charts are left untouched.
        """
        Rule = self.env["hr.salary.rule"]
        for company in self.filtered(lambda c: c.chart_template == "ca_2023"):
            chart = self.env["account.chart.template"].with_company(company)
            for xmlid, codes in _CA_2023_ON_RULE_ACCOUNTS.items():
                rule = Rule.browse(
                    self.env.ref(f"l10n_ca_on_payroll.{xmlid}").id
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
