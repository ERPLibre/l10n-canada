# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ca_bad_debt_origin_id = fields.Many2one(
        "account.move",
        string="Bad Debt of Invoice",
        readonly=True,
        copy=False,
        index="btree_not_null",
        help="Customer invoice whose bad debt this entry writes off or recovers.",
    )
    l10n_ca_bad_debt_type = fields.Selection(
        [("write_off", "Bad debt write-off"), ("recovery", "Bad debt recovery")],
        string="Bad Debt Operation",
        readonly=True,
        copy=False,
    )
    l10n_ca_bad_debt_move_ids = fields.One2many(
        "account.move",
        "l10n_ca_bad_debt_origin_id",
        string="Bad Debt Entries",
        readonly=True,
    )
    l10n_ca_bad_debt_written_off = fields.Monetary(
        string="Written Off as Bad Debt",
        compute="_compute_l10n_ca_bad_debt",
        currency_field="company_currency_id",
    )
    l10n_ca_bad_debt_recovered = fields.Monetary(
        string="Bad Debt Recovered",
        compute="_compute_l10n_ca_bad_debt",
        currency_field="company_currency_id",
    )

    @api.depends(
        "l10n_ca_bad_debt_move_ids.state", "l10n_ca_bad_debt_move_ids.line_ids.balance"
    )
    def _compute_l10n_ca_bad_debt(self):
        """Sum the receivable side of the posted bad debt entries.

        A write-off credits the receivable by the amount written off, a
        recovery debits it by the amount recovered.
        """
        for move in self:
            written_off = recovered = 0.0
            for entry in move.l10n_ca_bad_debt_move_ids.filtered(
                lambda m: m.state == "posted"
            ):
                receivable = sum(
                    entry.line_ids.filtered(
                        lambda l: l.account_id.account_type == "asset_receivable"
                    ).mapped("balance")
                )
                if entry.l10n_ca_bad_debt_type == "write_off":
                    written_off -= receivable
                else:
                    recovered += receivable
            move.l10n_ca_bad_debt_written_off = written_off
            move.l10n_ca_bad_debt_recovered = recovered

    def action_l10n_ca_bad_debt(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_ca_tax_return.action_l10n_ca_bad_debt_wizard"
        )
        action["context"] = {"default_move_id": self.id}
        return action

    def action_l10n_ca_open_bad_debt_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Bad Debt Entries"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("l10n_ca_bad_debt_origin_id", "=", self.id)],
            "context": {"create": False},
        }
