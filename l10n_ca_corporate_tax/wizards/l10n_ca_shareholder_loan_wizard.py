# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo import api, fields, models


class L10nCaShareholderLoanWizard(models.TransientModel):
    _name = "l10n.ca.shareholder.loan.wizard"
    _description = "Compute Shareholder Loan Follow-up"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    date_from = fields.Date(string="Fiscal Year Start", required=True)
    date_to = fields.Date(string="Fiscal Year End", required=True)
    as_of = fields.Date(
        string="Situation As Of",
        required=True,
        default=fields.Date.context_today,
        help="Repayments recorded after this date are ignored.",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        company = self.env.company
        today = fields.Date.context_today(self)
        current_from, _current_to = company._l10n_ca_fiscal_year(today)
        date_from, date_to = company._l10n_ca_fiscal_year(
            current_from - datetime.timedelta(days=1)
        )
        values.setdefault("date_from", date_from)
        values.setdefault("date_to", date_to)
        return values

    def action_compute(self):
        self.ensure_one()
        records = self.env["l10n.ca.shareholder.loan"]._l10n_ca_compute(
            self.company_id, self.date_from, self.date_to, self.as_of
        )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_ca_corporate_tax.action_l10n_ca_shareholder_loan"
        )
        action["domain"] = [("id", "in", records.ids)]
        return action
