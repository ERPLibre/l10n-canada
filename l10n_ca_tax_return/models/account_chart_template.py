# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.fields import Command

from odoo.addons.account.models.chart_template import template

# Sales taxes of ca_2023 whose base reaches GST34 line 91 but not FPZ-500
# line 101 in l10n_ca. Line 101 of both returns is the total revenue of the
# period, zero-rated exports and exempt supplies included; it is reported
# for information and does not enter the net tax.
LINE_101_TAXES = ("int_sale_tax_0", "exempt_sale_tax_0")

LINE_101_REPARTITION = [
    {
        "repartition_type": "base",
        "document_type": "invoice",
        "tag_ids": "+Ca91||+CaQc101",
    },
    {"repartition_type": "tax", "document_type": "invoice"},
    {
        "repartition_type": "base",
        "document_type": "refund",
        "tag_ids": "-Ca91||-CaQc101",
    },
    {"repartition_type": "tax", "document_type": "refund"},
]


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ca_2023", "account.tax")
    def _get_ca_l10n_ca_tax_return_account_tax(self):
        """Replace the repartition of the 0% international and exempt taxes.

        Template functions of a model are merged by xmlid with a shallow
        update, so the whole repartition list is given. The tags are names
        here and are resolved to ids like the CSV of l10n_ca.
        """
        data = {
            xmlid: {
                "repartition_line_ids": [
                    Command.create(dict(values)) for values in LINE_101_REPARTITION
                ]
            }
            for xmlid in LINE_101_TAXES
        }
        self._deref_account_tags("ca_2023", data)
        return data

    @template("ca_2023", "res.company")
    def _get_ca_l10n_ca_tax_return_res_company(self):
        return {
            self.env.company.id: {
                "l10n_ca_gst_authority_account_id": "l10n_ca_221210",
                "l10n_ca_qst_authority_account_id": "l10n_ca_221210",
                "l10n_ca_quick_method_gain_account_id": "l10n_ca_413300",
            },
        }
