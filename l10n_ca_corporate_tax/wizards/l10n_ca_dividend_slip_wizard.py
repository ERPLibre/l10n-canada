# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64

from odoo import fields, models


class L10nCaDividendSlipWizard(models.TransientModel):
    _name = "l10n.ca.dividend.slip.wizard"
    _description = "Generate T5 and RL-3 Dividend Slips"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    year = fields.Integer(
        string="Calendar Year",
        required=True,
        default=lambda self: fields.Date.context_today(self).year - 1,
    )
    slip_ids = fields.Many2many("l10n.ca.dividend.slip", string="Slips", readonly=True)
    t5_count = fields.Integer(string="T5 Slips", readonly=True)
    rl3_count = fields.Integer(string="RL-3 Slips", readonly=True)
    t5_box_24 = fields.Monetary(string="Total T5 Box 24", readonly=True)
    t5_box_25 = fields.Monetary(string="Total T5 Box 25", readonly=True)
    t5_box_26 = fields.Monetary(string="Total T5 Box 26", readonly=True)
    t5_box_10 = fields.Monetary(string="Total T5 Box 10", readonly=True)
    t5_box_11 = fields.Monetary(string="Total T5 Box 11", readonly=True)
    t5_box_12 = fields.Monetary(string="Total T5 Box 12", readonly=True)
    rl3_box_a1 = fields.Monetary(string="Total RL-3 Box A1", readonly=True)
    rl3_box_a2 = fields.Monetary(string="Total RL-3 Box A2", readonly=True)
    rl3_box_b = fields.Monetary(string="Total RL-3 Box B", readonly=True)
    rl3_box_c = fields.Monetary(string="Total RL-3 Box C", readonly=True)
    csv_file = fields.Binary(string="CSV File", readonly=True, attachment=False)
    csv_filename = fields.Char(readonly=True)

    def action_generate(self):
        """Rebuild the slips of the year and show the summary totals."""
        self.ensure_one()
        slips = self.env["l10n.ca.dividend.slip"]._l10n_ca_generate(
            self.company_id, self.year
        )
        values = slips._l10n_ca_summary()
        values.update(
            slip_ids=[fields.Command.set(slips.ids)],
            csv_file=base64.b64encode(slips._l10n_ca_csv().encode("utf-8")),
            csv_filename=f"dividend_slips_{self.year}.csv",
        )
        self.write(values)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_slips(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_ca_corporate_tax.action_l10n_ca_dividend_slip"
        )
        action["domain"] = [("id", "in", self.slip_ids.ids)]
        return action
