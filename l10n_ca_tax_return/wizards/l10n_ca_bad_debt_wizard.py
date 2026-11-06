# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

# Return lines of the bad debt adjustments, by the tag of the collected tax
# line of the invoice: a write-off is deducted on lines 107 (GST/HST) and
# 207 (QST), a recovery is added on lines 104 and 204. GST34 and FPZ-500
# share the numbers of the GST/HST lines.
BAD_DEBT_TAGS = {
    "Ca103": {"write_off": ("Ca107", "CaQc107"), "recovery": ("Ca104", "CaQc104")},
    "CaQc203": {"write_off": ("CaQc207",), "recovery": ("CaQc204",)},
}


class L10nCaBadDebtWizard(models.TransientModel):
    _name = "l10n.ca.bad.debt.wizard"
    _description = "Canadian Bad Debt Adjustment"

    move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]",
    )
    company_id = fields.Many2one(related="move_id.company_id")
    currency_id = fields.Many2one(related="move_id.company_currency_id")
    operation = fields.Selection(
        [("write_off", "Write off"), ("recovery", "Recover")],
        required=True,
        default="write_off",
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Monetary(
        compute="_compute_amount",
        store=True,
        precompute=True,
        readonly=False,
        help="Write-off: unpaid amount, taxes included. Recovery: amount "
        "received on the written-off debt, taxes included.",
    )
    account_id = fields.Many2one(
        "account.account",
        compute="_compute_account_id",
        store=True,
        precompute=True,
        readonly=False,
        required=True,
        check_company=True,
        help="Bad debt expense on a write-off, income on a recovery.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        compute="_compute_journal_id",
        store=True,
        precompute=True,
        readonly=False,
        required=True,
        check_company=True,
        domain="[('type', '=', 'general')]",
    )
    gst_amount = fields.Monetary(
        string="GST/HST Adjustment", compute="_compute_tax_amounts"
    )
    qst_amount = fields.Monetary(
        string="QST Adjustment", compute="_compute_tax_amounts"
    )

    @api.depends("move_id", "operation")
    def _compute_amount(self):
        for wizard in self:
            move = wizard.move_id
            if wizard.operation == "write_off":
                wizard.amount = move.amount_residual
            else:
                wizard.amount = (
                    move.l10n_ca_bad_debt_written_off - move.l10n_ca_bad_debt_recovered
                )

    @api.depends("move_id", "operation")
    def _compute_account_id(self):
        for wizard in self:
            company = wizard.move_id.company_id
            wizard.account_id = (
                company.l10n_ca_bad_debt_recovery_account_id
                if wizard.operation == "recovery"
                and company.l10n_ca_bad_debt_recovery_account_id
                else company.l10n_ca_bad_debt_account_id
            )

    @api.depends("move_id")
    def _compute_journal_id(self):
        for wizard in self:
            wizard.journal_id = (
                wizard.move_id.company_id._l10n_ca_tax_closing_journal()
                if wizard.move_id
                else False
            )

    @api.depends("move_id", "amount")
    def _compute_tax_amounts(self):
        for wizard in self:
            portions = wizard._tax_portions() if wizard.move_id else []
            wizard.gst_amount = sum(p for __, key, p in portions if key == "Ca103")
            wizard.qst_amount = sum(p for __, key, p in portions if key == "CaQc203")

    def _tax_portions(self):
        """Return [(tax line, collected tag, tax portion)] of ``amount``.

        Excise Tax Act s. 231(1) and (3): tax portion = tax of the supply x
        amount / total of the consideration, tax and provincial tax. The
        invoice total in company currency is that total, so each tax line
        of the invoice gives its prorated share. Tax lines without a GST/HST
        or QST collected tag are ignored. An invoice accounted under the
        quick method gives no portion: the quick method allows no bad debt
        adjustment on the supplies its remittance rate covers, so the whole
        amount goes to the expense or income account.
        """
        self.ensure_one()
        move = self.move_id
        currency = move.company_currency_id
        total = abs(move.amount_total_signed)
        portions = []
        if not total or self._is_quick_method_supply():
            return portions
        for line in move.line_ids.filtered("tax_line_id"):
            names = {
                tag.with_context(lang="en_US").name[1:] for tag in line.tax_tag_ids
            }
            key = next((k for k in BAD_DEBT_TAGS if k in names), None)
            if key:
                portion = currency.round(self.amount * abs(line.balance) / total)
                portions.append((line, key, portion))
        return portions

    def _is_quick_method_supply(self):
        """Whether the invoice falls in the quick method of its company.

        True when the company uses the quick method and the invoice is dated
        on or after the effective date of the election (any date when the
        election has no date).
        """
        company = self.move_id.company_id
        election = company.l10n_ca_quick_method_date
        return bool(company.l10n_ca_quick_method) and (
            not election or self.move_id.date >= election
        )

    def _adjustment_tags(self, key, negate):
        country = self.env.ref("base.ca")
        Tag = self.env["account.account.tag"]
        tags = Tag
        for formula in BAD_DEBT_TAGS[key][self.operation]:
            tags |= Tag._get_tax_tags(formula, country.id).filtered(
                lambda t, n=negate: t.tax_negate == n
            )
        return tags

    def action_confirm(self):
        """Post the bad debt entry.

        Write-off: credit the receivable, debit each tax account by its tax
        portion with the "+" deduction tags, debit the expense with the
        rest; the entry is reconciled with the invoice. Recovery: debit the
        receivable, credit each tax account by its portion with the "-"
        addition tags (a credit shows as a positive addition), credit the
        income with the rest; the payment of the customer is then matched
        with that receivable.
        """
        self.ensure_one()
        move = self.move_id
        currency = move.company_currency_id
        if move.move_type != "out_invoice" or move.state != "posted":
            raise UserError(_("Select a posted customer invoice."))
        if move.currency_id != move.company_currency_id:
            raise UserError(
                _("Bad debt adjustments support invoices in company currency only.")
            )
        if currency.compare_amounts(self.amount, 0.0) <= 0:
            raise UserError(_("The amount must be positive."))
        write_off = self.operation == "write_off"
        limit = (
            move.amount_residual
            if write_off
            else move.l10n_ca_bad_debt_written_off - move.l10n_ca_bad_debt_recovered
        )
        if currency.compare_amounts(self.amount, limit) > 0:
            raise UserError(
                _(
                    "The amount exceeds %(limit).2f, the %(what)s of the invoice.",
                    limit=limit,
                    what=(
                        _("unpaid balance") if write_off else _("unrecovered bad debt")
                    ),
                )
            )
        sign = 1.0 if write_off else -1.0
        receivables = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        receivable = receivables[:1]
        label = (
            _("Bad debt write-off of %s", move.name)
            if write_off
            else _("Bad debt recovery of %s", move.name)
        )
        commands = [
            Command.create(
                {
                    "name": label,
                    "account_id": receivable.account_id.id,
                    "partner_id": move.commercial_partner_id.id,
                    "balance": -sign * self.amount,
                }
            )
        ]
        taxes = 0.0
        for line, key, portion in self._tax_portions():
            if currency.is_zero(portion):
                continue
            taxes += portion
            commands.append(
                Command.create(
                    {
                        "name": label,
                        "account_id": line.account_id.id,
                        "partner_id": move.commercial_partner_id.id,
                        "balance": sign * portion,
                        "tax_tag_ids": [
                            Command.set(self._adjustment_tags(key, not write_off).ids)
                        ],
                    }
                )
            )
        commands.append(
            Command.create(
                {
                    "name": label,
                    "account_id": self.account_id.id,
                    "partner_id": move.commercial_partner_id.id,
                    "balance": sign * currency.round(self.amount - taxes),
                }
            )
        )
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal_id.id,
                "date": self.date,
                "ref": label,
                "l10n_ca_bad_debt_origin_id": move.id,
                "l10n_ca_bad_debt_type": self.operation,
                "line_ids": commands,
            }
        )
        entry.action_post()
        if write_off:
            (
                receivables.filtered(
                    lambda line: line.account_id == receivable.account_id
                    and not line.reconciled
                )
                + entry.line_ids.filtered(
                    lambda line: line.account_id == receivable.account_id
                )
            ).reconcile()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": entry.id,
            "view_mode": "form",
        }
