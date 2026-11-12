# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_ca_nu_payroll_tax_exempt = fields.Boolean(
        string="Exempt from the Nunavut Payroll Tax",
        help="No Nunavut payroll tax is withheld from the pays of this "
        "contract. For an employee whose remuneration is not subject: a "
        "member of a religious order with a vow of perpetual poverty (Income "
        "Tax Act, s. 110(2)), or an employee who normally works outside "
        "Nunavut and whose remuneration from the company in the year is not "
        "expected to exceed the prescribed amount of 5,000 (Payroll Tax Act, "
        "s. 3(2.2); Payroll Tax Regulations, s. 2).",
    )
