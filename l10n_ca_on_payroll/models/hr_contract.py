# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

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

    def _l10n_ca_on_dependants(self):
        """Return the dependants counted in factor Y of the tax reduction."""
        self.ensure_one()
        return max(0, self.l10n_ca_on_dependants_under_19) + max(
            0, self.l10n_ca_on_disabled_dependants
        )
