# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_ca_qc_sbd_majority_shareholder = fields.Boolean(
        string="Majority Voting Shareholder",
        groups="hr.group_hr_user",
        help="The employee holds, directly or indirectly, the majority of the "
        "voting shares of the company. The hours of the done payslips count "
        "in the Quebec small business deduction remunerated hours multiplied "
        "by the shareholder hours factor.",
    )
