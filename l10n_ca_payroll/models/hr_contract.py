# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models

# Pay periods per year of each ``schedule_pay`` of the OCA payroll.
# "bi-monthly" is read as twice a month (semi-monthly, 24 periods), the
# frequency the CRA tables call semi-monthly; the pay period count stays
# editable on the contract for a 27-period bi-weekly or 53-period weekly
# year.
SCHEDULE_PAY_PERIODS = {
    "monthly": 12,
    "quarterly": 4,
    "semi-annually": 2,
    "annually": 1,
    "weekly": 52,
    "bi-weekly": 26,
    "bi-monthly": 24,
}


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_ca_province_id = fields.Many2one(
        "res.country.state",
        string="Province of Employment",
        domain="[('country_id.code', '=', 'CA')]",
        default=lambda self: self._default_l10n_ca_province(),
        help="Province or territory where the employee reports for work. "
        "It selects the provincial tax, the pension plan (CPP or QPP) and "
        "the EI rate.",
    )
    l10n_ca_pay_periods = fields.Integer(
        string="Pay Periods per Year",
        compute="_compute_l10n_ca_pay_periods",
        store=True,
        readonly=False,
        help="P of the CRA payroll formulas. Computed from the scheduled "
        "pay; set 27 or 53 for a year with an extra bi-weekly or weekly "
        "pay.",
    )
    l10n_ca_td1_federal_type = fields.Selection(
        [
            ("basic", "Basic personal amount"),
            ("custom", "Total claim amount from the TD1"),
        ],
        string="Federal TD1 Claim",
        default="basic",
        required=True,
        help="Basic personal amount: the claim is the federal basic "
        "personal amount of the year, reduced for high incomes, as when "
        "the employee files no TD1. Total claim amount: the amount of the "
        "TD1 form, 0 for claim code 0.",
    )
    l10n_ca_td1_federal_amount = fields.Monetary(
        string="Federal TD1 Total Claim Amount",
    )
    l10n_ca_td1_federal_bpa = fields.Monetary(
        string="Federal Basic Personal Amount",
        compute="_compute_l10n_ca_td1_federal_bpa",
        help="Maximum federal basic personal amount in force today. The "
        "payslip reduces it for an annual income above the phase-out "
        "threshold.",
    )
    l10n_ca_additional_federal_tax = fields.Monetary(
        string="Additional Federal Tax per Pay",
        help="Additional tax requested by the employee on the TD1 form.",
    )
    l10n_ca_prescribed_zone_deduction = fields.Monetary(
        string="Prescribed Zone Deduction (Annual)",
        help="HD of the CRA formulas: annual deduction for living in a "
        "prescribed northern zone claimed on the TD1. It lowers the annual "
        "taxable income A of the federal tax and of the provincial or "
        "territorial tax computed with the CRA formulas.",
    )
    l10n_ca_federal_other_credits = fields.Monetary(
        string="Other Federal Tax Credits (Annual)",
        help="K3 of the CRA formulas: other federal non-refundable tax "
        "credits authorized by a tax services office, as an annual credit "
        "amount.",
    )
    l10n_ca_rpp_amount = fields.Monetary(
        string="RPP Contribution per Pay",
        help="Employee contribution to a registered pension plan withheld "
        "from each pay by salary rule CA_RPP, with the RPP input of the "
        "payslip. It lowers the taxable income of the pay (F of the CRA and "
        "Revenu Quebec formulas) and is reported in box 20 of the T4.",
    )
    l10n_ca_rrsp_amount = fields.Monetary(
        string="RRSP Contribution per Pay",
        help="Employee contribution to an RRSP, a PRPP or a VRSP withheld "
        "from each pay by salary rule CA_RRSP, with the RRSP input of the "
        "payslip. It lowers the taxable income of the pay (F of the CRA and "
        "Revenu Quebec formulas).",
    )
    l10n_ca_union_dues_amount = fields.Monetary(
        string="Union Dues per Pay",
        help="Union dues withheld from each pay by salary rule CA_UNION, with "
        "the union dues input of the payslip. They lower the taxable income "
        "of the CRA formulas (U1), not the Quebec one, and are reported in "
        "box 44 of the T4 and box F of the RL-1 unless the union issues its "
        "own receipts.",
    )
    l10n_ca_union_issues_receipts = fields.Boolean(
        string="Union Issues Receipts",
        help="The union issues receipts for the dues: they still lower the "
        "withholding, but box 44 of the T4 and box F of the RL-1 stay empty, "
        "since the CRA and Revenu Quebec have the employer report the dues "
        "only under an agreement that the union issues no receipts.",
    )
    l10n_ca_support_amount = fields.Monetary(
        string="Support Payments per Pay",
        help="Alimony or maintenance payments withheld from each pay under a "
        "legal document dated before May 1, 1997, as authorized by a CRA tax "
        "services office (salary rule CA_SUPPORT, with the support input of "
        "the payslip). They lower the taxable income of the CRA formulas "
        "(F2), not the Quebec one. When the order caps the payment at a "
        "percentage of the net salary, enter the amount that results from "
        "that cap.",
    )
    l10n_ca_t4_dental_code = fields.Selection(
        [
            ("1", "1 - Not eligible to any dental care coverage"),
            ("2", "2 - Payee only"),
            ("3", "3 - Payee, spouse and dependent children"),
            ("4", "4 - Payee and spouse"),
            ("5", "5 - Payee and dependent children"),
        ],
        string="Employer-Offered Dental Benefits (T4 Box 45)",
        default="1",
        required=True,
        help="Dental coverage offered to the employee by the employer, "
        "whether or not the employee uses it.",
    )
    l10n_ca_cpp_exempt = fields.Boolean(
        string="Exempt from CPP/QPP",
        help="No pension plan contribution is deducted, e.g. an employee "
        "who receives a disability pension or filed an election to stop "
        "contributing.",
    )
    l10n_ca_ei_exempt = fields.Boolean(
        string="Exempt from EI",
        help="No EI premium is deducted, e.g. an employee who controls "
        "more than 40% of the voting shares of the corporation.",
    )
    l10n_ca_province_code = fields.Char(related="l10n_ca_province_id.code")
    l10n_ca_prov_computed = fields.Boolean(
        string="Provincial Tax Computed",
        compute="_compute_l10n_ca_prov_computed",
        help="An installed module computes the income tax of the province "
        "of employment with the CRA formulas.",
    )
    l10n_ca_prov_td1_type = fields.Selection(
        [
            ("basic", "Basic personal amount"),
            ("custom", "Total claim amount from the TD1"),
            ("exempt", "Exempt (claim code E)"),
        ],
        string="Provincial TD1 Claim",
        default="basic",
        required=True,
        help="Provincial or territorial TD1 of the province of employment "
        "(TD1ON, TD1BC, ...). Basic personal amount: the claim is the "
        "basic personal amount of the year, as when the employee files no "
        "provincial TD1. Total claim amount: the amount of the form, 0 for "
        "claim code 0. Exempt: the employee expects a total income below "
        "the claim; no provincial tax is withheld, except the amounts the "
        "province levies whatever the claim, such as the Ontario Health "
        "Premium.",
    )
    l10n_ca_prov_td1_amount = fields.Monetary(
        string="Provincial TD1 Total Claim Amount",
        help="TCP of the T4127 formulas: total of the provincial or "
        "territorial personal tax credit amounts of the TD1. Enter the "
        "amount of the form of the year of the pay: the payslip does not "
        "index it.",
    )
    l10n_ca_prov_bpa = fields.Monetary(
        string="Provincial Basic Personal Amount",
        compute="_compute_l10n_ca_prov_bpa",
        help="Basic personal amount of the province of employment in force "
        "today; for an income-tested amount, its maximum.",
    )
    l10n_ca_prov_other_credits = fields.Monetary(
        string="Other Provincial Tax Credits (Annual)",
        help="K3P of the T4127 formulas: other provincial or territorial "
        "non-refundable tax credits authorized by a tax services office, "
        "such as medical expenses or charitable donations, as an annual "
        "credit amount.",
    )
    l10n_ca_prov_additional_tax = fields.Monetary(
        string="Additional Provincial Tax per Pay",
        help="Additional provincial or territorial income tax the employee "
        "asks to have withheld on each pay.",
    )
    l10n_ca_lsvcc_amount = fields.Monetary(
        string="Labour-Sponsored Fund Shares per Pay",
        help="Amount withheld from each pay to buy approved shares of a "
        "labour-sponsored venture capital corporation (salary rule "
        "CA_LSVCC, with the input of the payslip). The provinces that grant "
        "a labour-sponsored funds tax credit lower the provincial tax by "
        "it (LCP of the T4127 formulas).",
    )
    l10n_ca_wcb_exempt = fields.Boolean(
        string="Not Covered by Workers' Compensation",
        help="No workers' compensation premium on this remuneration, e.g. "
        "a proprietor or an executive officer without optional coverage.",
    )

    @api.model
    def _default_l10n_ca_province(self):
        state = self.env.company.state_id
        return state if state.country_id.code == "CA" else False

    @api.depends("schedule_pay")
    def _compute_l10n_ca_pay_periods(self):
        for contract in self:
            contract.l10n_ca_pay_periods = SCHEDULE_PAY_PERIODS.get(
                contract.schedule_pay, 12
            )

    def _compute_l10n_ca_td1_federal_bpa(self):
        today = fields.Date.context_today(self)
        for contract in self:
            company = contract.company_id or self.env.company
            contract.l10n_ca_td1_federal_bpa = company._l10n_ca_param(
                "l10n_ca.federal.bpa_max", today, default=0.0
            )

    @api.depends("l10n_ca_province_id")
    def _compute_l10n_ca_prov_computed(self):
        prefixes = self.env["hr.payslip"]._l10n_ca_province_prefixes()
        for contract in self:
            contract.l10n_ca_prov_computed = (
                contract.l10n_ca_province_id.code in prefixes
            )

    @api.depends("l10n_ca_province_id")
    def _compute_l10n_ca_prov_bpa(self):
        today = fields.Date.context_today(self)
        Payslip = self.env["hr.payslip"]
        for contract in self:
            prefix = Payslip._l10n_ca_province_prefix(contract.l10n_ca_province_id)
            company = contract.company_id or self.env.company
            contract.l10n_ca_prov_bpa = (
                company._l10n_ca_param(f"{prefix}.bpa", today, default=0.0)
                if prefix
                else 0.0
            )

    def _l10n_ca_federal_claim(self, net_income, date):
        """Return TC, the annual federal claim amount of the T4127 formulas.

        ``net_income`` is the annual net income NI used by the phase-out of
        the basic personal amount when the contract claims it.
        """
        self.ensure_one()
        if self.l10n_ca_td1_federal_type == "custom":
            return self.l10n_ca_td1_federal_amount
        return self.env["hr.payslip"]._l10n_ca_federal_bpa(
            self.company_id or self.env.company, net_income, date
        )
