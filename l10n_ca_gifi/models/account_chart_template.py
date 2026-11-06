# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ca_2023", "account.account")
    def _get_l10n_ca_gifi_account_account(self):
        """GIFI code of each account of the ca_2023 chart.

        Read from ``data/template/account.account-ca_2023.csv`` of this
        module, merged by the chart loader into the account values.
        """
        return self._parse_csv("ca_2023", "account.account", module="l10n_ca_gifi")

    def _post_load_data(self, template_code, company, template_data):
        result = super()._post_load_data(template_code, company, template_data)
        if template_code == "ca_2023":
            (company or self.env.company)._l10n_ca_gifi_assign_default_codes()
        return result
