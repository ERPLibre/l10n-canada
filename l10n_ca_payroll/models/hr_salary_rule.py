# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    def _compute_rule(self, localdict):
        """Name the payslip line in the language of the computing user.

        The payroll engine dispatches to ``_compute_rule_<type>`` through
        ``api.call_kw``, which replaces the context with an empty one: the
        rule name read there is the English source. A rule that sets no
        ``result_name`` takes its name again from this recordset, whose
        context keeps the language. A ``result_name`` is kept as computed.
        """
        result = super()._compute_rule(localdict)
        if not localdict.get("result_name"):
            result["name"] = self.name
        return result
