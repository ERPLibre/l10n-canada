# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_ca_province_code = fields.Char(related="l10n_ca_province_id.code")
    l10n_ca_on_td1_type = fields.Selection(
        [
            ("basic", "Basic personal amount"),
            ("custom", "Total claim amount from the TD1ON"),
            ("exempt", "Exempt (claim code E)"),
        ],
        string="Ontario TD1ON Claim",
        default="basic",
        required=True,
        help="Basic personal amount: the claim is the Ontario basic "
        "personal amount of the year, as when the employee files no TD1ON. "
        "Total claim amount: the amount of line 10 of the TD1ON, 0 for "
        "claim code 0. Exempt: the employee expects a total income below "
        "the claim; no Ontario tax is withheld except the Ontario Health "
        "Premium on an annual income above 20,000. A non-resident whose "
        "federal claim is 0 has an Ontario claim of 0 as well: choose the "
        "total claim amount and leave it at 0.",
    )
    l10n_ca_on_td1_amount = fields.Monetary(
        string="TD1ON Total Claim Amount",
        help="TCP of the T4127 formulas: total of the Ontario personal tax "
        "credit amounts of the TD1ON. Enter the amount of the form of the "
        "year of the pay: the payslip does not index it.",
    )
    l10n_ca_on_bpa = fields.Monetary(
        string="Ontario Basic Personal Amount",
        compute="_compute_l10n_ca_on_bpa",
        help="Ontario basic personal amount in force today.",
    )
    l10n_ca_on_dependants_under_19 = fields.Integer(
        string="Dependants Under Age 19",
        help="Number of dependants under age 19 the employee declared on "
        "the TD1ON or in a written or electronic request. Each one adds "
        "the amount per dependant to factor Y of the Ontario tax "
        "reduction.",
    )
    l10n_ca_on_disabled_dependants = fields.Integer(
        string="Disabled Dependants",
        help="Number of disabled dependants the employee declared on the "
        "TD1ON or in a written or electronic request. Each one adds the "
        "amount per dependant to factor Y of the Ontario tax reduction.",
    )
    l10n_ca_on_other_credits = fields.Monetary(
        string="Other Ontario Tax Credits (Annual)",
        help="K3P of the T4127 formulas: other Ontario non-refundable tax "
        "credits authorized by a tax services office, such as medical "
        "expenses or charitable donations, as an annual credit amount.",
    )
    l10n_ca_on_additional_tax = fields.Monetary(
        string="Additional Ontario Tax per Pay",
        help="Additional Ontario income tax the employee asks to have "
        "withheld on each pay.",
    )
    l10n_ca_on_wsib_exempt = fields.Boolean(
        string="Not Covered by the WSIB",
        help="No WSIB premium on this remuneration, e.g. an executive "
        "officer of a corporation outside construction without optional "
        "insurance.",
    )

    def _compute_l10n_ca_on_bpa(self):
        today = fields.Date.context_today(self)
        for contract in self:
            company = contract.company_id or self.env.company
            contract.l10n_ca_on_bpa = company._l10n_ca_param(
                "l10n_ca.on.bpa", today, default=0.0
            )

    def _l10n_ca_on_claim(self, date):
        """Return TCP, the annual Ontario claim amount at ``date``.

        The amount of the TD1ON when the contract enters one, else the
        Ontario basic personal amount of the year of ``date``.
        """
        self.ensure_one()
        if self.l10n_ca_on_td1_type == "custom":
            return self.l10n_ca_on_td1_amount
        return (self.company_id or self.env.company)._l10n_ca_param(
            "l10n_ca.on.bpa", date
        )

    def _l10n_ca_on_dependants(self):
        """Return the dependants counted in factor Y of the tax reduction."""
        self.ensure_one()
        return max(0, self.l10n_ca_on_dependants_under_19) + max(
            0, self.l10n_ca_on_disabled_dependants
        )
