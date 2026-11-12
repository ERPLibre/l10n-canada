# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models

from odoo.addons.l10n_ca_time_parameter.tools import marginal_rate


class L10nCaPayrollProvinceAccount(models.Model):
    """Accounts of a company with the payroll bodies of one province.

    One record per company and province of employment: the employer payroll
    tax of the province (Ontario and British Columbia Employer Health Tax,
    Manitoba and Newfoundland and Labrador health and post-secondary
    education tax) and the workers' compensation board. The province module
    supplies the dated parameters ``<prefix>.employer_tax.*`` and
    ``<prefix>.wcb.max_insurable`` that the payslip applies with these
    company figures.
    """

    _name = "l10n_ca.payroll.province.account"
    _description = "Provincial Payroll Account"
    _order = "company_id, province_id"
    _rec_name = "province_id"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    province_id = fields.Many2one(
        "res.country.state",
        string="Province",
        required=True,
        domain="[('country_id.code', '=', 'CA')]",
    )
    has_employer_tax = fields.Boolean(
        compute="_compute_has_employer_tax",
        help="The province levies a tax on the remuneration paid by the "
        "employer, computed by an installed module.",
    )
    employer_tax_account_number = fields.Char(
        string="Employer Tax Account Number",
        help="Account number of the company for the employer payroll tax of "
        "the province.",
    )
    employer_tax_eligible = fields.Boolean(
        string="Eligible for the Exemption",
        default=True,
        help="The employer deducts the exemption of the year from its total "
        "remuneration in the province. Public-sector employers and the "
        "other employers that the statute of the province excludes pay the "
        "tax on their whole remuneration.",
    )
    employer_tax_charity = fields.Boolean(
        string="Registered Charity",
        help="A registered charity keeps the exemption whatever its total "
        "remuneration in the province.",
    )
    employer_tax_associated = fields.Boolean(
        string="Associated Employer",
        help="The company belongs to a group of associated employers that "
        "shares one exemption by an allocation agreement.",
    )
    employer_tax_allocated_exemption = fields.Monetary(
        string="Exemption Allocated to the Company",
        help="Share of the group exemption allocated to the company. The "
        "company takes the lesser of this amount and the exemption of the "
        "year. Enter 0 when the group allocates nothing to the company or "
        "when the total remuneration of the group exceeds the exemption "
        "threshold.",
    )
    employer_tax_basis = fields.Selection(
        [
            ("previous_year", "Total remuneration of the previous year"),
            ("estimate", "Estimated total remuneration of the year"),
        ],
        string="Rate Basis",
        default="previous_year",
        required=True,
        help="Annual total remuneration in the province that selects the "
        "rate and, for an employer not associated, decides whether the "
        "exemption applies. The tax of the year is set on the actual "
        "remuneration by the annual return; a new employer or one whose "
        "payroll changes enters an estimate of the current year.",
    )
    employer_tax_previous_payroll = fields.Monetary(
        string="Previous Year Total Remuneration",
        help="Total remuneration paid in the province by the company in the "
        "previous year, all accounts combined, before the exemption.",
    )
    employer_tax_estimated_payroll = fields.Monetary(
        string="Estimated Total Remuneration",
        help="Total remuneration the company expects to pay in the province "
        "in the current year, all accounts combined, before the exemption.",
    )
    wcb_account_number = fields.Char(
        string="Workers' Compensation Account Number",
        help="Firm or account number of the company at the workers' "
        "compensation board of the province.",
    )
    wcb_rate = fields.Float(
        string="Workers' Compensation Rate per $100",
        digits=(6, 4),
        help="Premium or assessment rate per $100 of insurable earnings of "
        "the annual notice of the board for the classification of the "
        "company. Leave 0 when the company has no account with the board: "
        "the payslip then computes no premium.",
    )

    _sql_constraints = [
        (
            "company_province_unique",
            "unique(company_id, province_id)",
            "A company has one payroll account per province.",
        ),
    ]

    @api.depends("province_id", "company_id")
    def _compute_has_employer_tax(self):
        Payslip = self.env["hr.payslip"]
        today = fields.Date.context_today(self)
        for account in self:
            prefix = Payslip._l10n_ca_province_prefix(account.province_id)
            account.has_employer_tax = bool(prefix) and bool(
                account.company_id._l10n_ca_param(
                    f"{prefix}.employer_tax.rates", today, default=None
                )
            )

    def _l10n_ca_employer_tax_payroll(self):
        """Return the annual total remuneration of the rate basis, 0 without
        an account."""
        if not self:
            return 0.0
        self.ensure_one()
        if self.employer_tax_basis == "estimate":
            return self.employer_tax_estimated_payroll
        return self.employer_tax_previous_payroll

    def _l10n_ca_employer_tax_rate(self, company, prefix, total_payroll, date):
        """Return the rate of the total remuneration ``total_payroll``.

        ``<prefix>.employer_tax.rates`` gives the rate of the last threshold
        that the total remuneration exceeds: a remuneration equal to a
        threshold stays at the lower rate.
        """
        rates = company._l10n_ca_param(f"{prefix}.employer_tax.rates", date)
        return marginal_rate(max(total_payroll or 0.0, 0.0), rates)

    def _l10n_ca_employer_tax_exemption(self, company, prefix, total_payroll, date):
        """Return the exemption of the year of ``date``.

        Without an account, the company is an eligible employer that is not
        associated. 0 for an employer that is not eligible. An associated
        employer takes the lesser of its allocated share and the exemption
        of the year. Another eligible employer takes the exemption of the
        year when ``total_payroll`` is at most
        ``<prefix>.employer_tax.exemption_threshold`` (no threshold: always)
        or when it is a registered charity, else 0. The exemption is not
        prorated for a part of the year.
        """
        param = company._l10n_ca_param
        exemption = param(f"{prefix}.employer_tax.exemption", date, default=0.0)
        if self and not self.employer_tax_eligible:
            return 0.0
        if self and self.employer_tax_associated:
            return max(0.0, min(self.employer_tax_allocated_exemption, exemption))
        threshold = param(
            f"{prefix}.employer_tax.exemption_threshold", date, default=None
        )
        if threshold is None or total_payroll <= threshold:
            return exemption
        if self and self.employer_tax_charity:
            return exemption
        return 0.0
