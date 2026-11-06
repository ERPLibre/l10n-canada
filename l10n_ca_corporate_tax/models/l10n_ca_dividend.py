# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

DIVIDEND_TYPES = [
    ("eligible", "Eligible"),
    ("non_eligible", "Other than eligible (ordinary)"),
]


class L10nCaDividend(models.Model):
    _name = "l10n.ca.dividend"
    _description = "Dividend to a Shareholder"
    _inherit = ["mail.thread"]
    _order = "resolution_date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="/")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    partner_id = fields.Many2one(
        "res.partner",
        string="Shareholder",
        required=True,
        tracking=True,
        domain="[('l10n_ca_shareholder', '=', True)]",
    )
    resolution_date = fields.Date(
        required=True,
        tracking=True,
        default=fields.Date.context_today,
        help="Date of the directors' resolution declaring the dividend.",
    )
    payment_date = fields.Date(
        tracking=True,
        help="Date the dividend is paid: it decides the calendar year of the "
        "T5 and RL-3 slips and the rates applied.",
    )
    amount = fields.Monetary(required=True, tracking=True)
    dividend_type = fields.Selection(
        DIVIDEND_TYPES,
        string="Type",
        required=True,
        default="non_eligible",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("declared", "Declared"),
            ("paid", "Paid"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
        copy=False,
    )
    payment_journal_id = fields.Many2one(
        "account.journal",
        string="Payment Journal",
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    declaration_move_id = fields.Many2one(
        "account.move", string="Declaration Entry", readonly=True, copy=False
    )
    payment_move_id = fields.Many2one(
        "account.move", string="Payment Entry", readonly=True, copy=False
    )
    warning_message = fields.Text(compute="_compute_warning_message")
    note = fields.Text()

    _sql_constraints = [
        (
            "l10n_ca_dividend_positive",
            "CHECK (amount > 0)",
            "A dividend must be positive.",
        ),
    ]

    @api.depends(
        "dividend_type",
        "amount",
        "partner_id",
        "resolution_date",
        "company_id.l10n_ca_grip_balance",
        "company_id.l10n_ca_grip_date",
    )
    def _compute_warning_message(self):
        for record in self:
            warnings = []
            if record.partner_id and not record.partner_id.l10n_ca_shareholder:
                warnings.append(_("The recipient is not flagged as a shareholder."))
            excess = record._l10n_ca_grip_excess()
            if excess > 0:
                warnings.append(
                    _(
                        "Eligible dividends of the fiscal year exceed the "
                        "general rate income pool (GRIP) by %(excess).2f: the "
                        "excess is an excessive eligible dividend designation "
                        "subject to Part III.1 tax. Consider designating it as "
                        "an ordinary dividend or electing under ITA s. 185.1(2).",
                        excess=excess,
                    )
                )
            record.warning_message = "\n".join(warnings) or False

    def _l10n_ca_grip_excess(self):
        """Return how much eligible dividends of the year exceed the GRIP.

        Sums this dividend and the other non-cancelled eligible dividends
        declared in the same fiscal year, from the GRIP date on, and
        compares them with the GRIP balance of the company settings.
        """
        self.ensure_one()
        if self.dividend_type != "eligible" or not self.resolution_date:
            return 0.0
        company = self.company_id
        date_from, date_to = company._l10n_ca_fiscal_year(self.resolution_date)
        if company.l10n_ca_grip_date and company.l10n_ca_grip_date > date_from:
            date_from = company.l10n_ca_grip_date
        others = self.search(
            [
                ("company_id", "=", company.id),
                ("dividend_type", "=", "eligible"),
                ("state", "!=", "cancel"),
                ("resolution_date", ">=", date_from),
                ("resolution_date", "<=", date_to),
                ("id", "not in", self.ids if isinstance(self.id, int) else []),
            ]
        )
        total = self.amount + sum(others.mapped("amount"))
        return total - company.l10n_ca_grip_balance

    # ------------------------------------------------------------------
    # Accounting
    # ------------------------------------------------------------------
    def _l10n_ca_check_configuration(self):
        company = self.company_id
        missing = []
        if not company.l10n_ca_dividend_account_id:
            missing.append(_("Dividends Declared Account"))
        if not company.l10n_ca_dividend_payable_account_id:
            missing.append(_("Dividends Payable Account"))
        if not company.l10n_ca_dividend_journal_id:
            missing.append(_("Dividend Declaration Journal"))
        if missing:
            raise UserError(
                _(
                    "Set the following in Invoicing (Accounting) > "
                    "Configuration > Settings > Owner-Manager Corporate Tax: %s",
                    ", ".join(missing),
                )
            )

    def action_declare(self):
        """Post the declaration: debit dividends declared, credit payable."""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a draft dividend can be declared."))
            record._l10n_ca_check_configuration()
            company = record.company_id
            payable = company.l10n_ca_dividend_payable_account_id
            types = dict(
                record._fields["dividend_type"]._description_selection(self.env)
            )
            label = _(
                "Dividend %(type)s - %(partner)s",
                type=types[record.dividend_type],
                partner=record.partner_id.display_name,
            )
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": record.resolution_date,
                    "journal_id": company.l10n_ca_dividend_journal_id.id,
                    "ref": label,
                    "line_ids": [
                        fields.Command.create(
                            {
                                "name": label,
                                "account_id": company.l10n_ca_dividend_account_id.id,
                                "partner_id": record.partner_id.id,
                                "debit": record.amount,
                            }
                        ),
                        fields.Command.create(
                            {
                                "name": label,
                                "account_id": payable.id,
                                "partner_id": record.partner_id.id,
                                "credit": record.amount,
                            }
                        ),
                    ],
                }
            )
            move.action_post()
            if record.name == "/":
                record.name = record._l10n_ca_next_name()
            record.write({"declaration_move_id": move.id, "state": "declared"})
        return True

    def _l10n_ca_next_name(self):
        """Return the next number of the company, dated by the resolution.

        Each company numbers its own dividends: its sequence is copied
        from the shared one on first use. The year of the number is the
        year of the resolution, not the year the button is clicked.
        """
        self.ensure_one()
        code = "l10n.ca.dividend"
        sequences = self.env["ir.sequence"].sudo()
        sequence = sequences.search(
            [("code", "=", code), ("company_id", "=", self.company_id.id)], limit=1
        )
        if not sequence:
            shared = self.env.ref(
                "l10n_ca_corporate_tax.seq_l10n_ca_dividend", raise_if_not_found=False
            )
            values = {"company_id": self.company_id.id, "number_next": 1}
            if shared:
                sequence = shared.sudo().copy(values)
            else:
                values.update(
                    name="Dividend", code=code, prefix="DIV/%(year)s/", padding=4
                )
                sequence = sequences.create(values)
        # Without date ranges, the prefix reads its year from the context
        # only: the sequence_date argument would be ignored.
        return sequence.with_context(ir_sequence_date=self.resolution_date).next_by_id()

    def action_pay(self):
        """Post the payment: debit payable, credit the bank, and reconcile."""
        for record in self:
            if record.state != "declared":
                raise UserError(_("Only a declared dividend can be paid."))
            if not record.payment_journal_id or not record.payment_date:
                raise UserError(_("Set the payment journal and the payment date."))
            journal = record.payment_journal_id
            if not journal.default_account_id:
                raise UserError(
                    _("The journal %s has no default account.", journal.display_name)
                )
            company = record.company_id
            payable = company.l10n_ca_dividend_payable_account_id
            label = _("Dividend payment - %s", record.partner_id.display_name)
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": record.payment_date,
                    "journal_id": journal.id,
                    "ref": label,
                    "line_ids": [
                        fields.Command.create(
                            {
                                "name": label,
                                "account_id": payable.id,
                                "partner_id": record.partner_id.id,
                                "debit": record.amount,
                            }
                        ),
                        fields.Command.create(
                            {
                                "name": label,
                                "account_id": journal.default_account_id.id,
                                "partner_id": record.partner_id.id,
                                "credit": record.amount,
                            }
                        ),
                    ],
                }
            )
            move.action_post()
            if payable.reconcile:
                (record.declaration_move_id.line_ids | move.line_ids).filtered(
                    lambda line, a=payable: line.account_id == a
                ).reconcile()
            record.write({"payment_move_id": move.id, "state": "paid"})
        return True

    def action_cancel(self):
        """Reverse the posted entries and cancel the dividend."""
        for record in self:
            moves = (record.declaration_move_id | record.payment_move_id).filtered(
                lambda m: m.state == "posted"
            )
            if moves:
                # The payable lines are matched together: unmatch them so
                # each reversal can match the line it cancels.
                moves.line_ids.filtered("reconciled").remove_move_reconcile()
                moves._reverse_moves(
                    [{"ref": _("Reversal of %s", m.ref or m.name)} for m in moves],
                    cancel=True,
                )
            record.state = "cancel"
        return True

    def action_draft(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(_("Only a cancelled dividend can be reset to draft."))
            record.write(
                {
                    "state": "draft",
                    "declaration_move_id": False,
                    "payment_move_id": False,
                }
            )
        return True

    # ------------------------------------------------------------------
    # Slip amounts
    # ------------------------------------------------------------------
    def _l10n_ca_slip_amounts(self):
        """Return the T5 and RL-3 amounts of one paid dividend.

        Rates are read at the payment date. Keys: ``taxable`` and
        ``fed_credit`` (federal), ``qc_taxable`` and ``qc_credit``
        (Quebec), each rounded to the cent.
        """
        self.ensure_one()
        company = self.company_id
        day = self.payment_date
        kind = "eligible" if self.dividend_type == "eligible" else "non_eligible"

        def param(code):
            return company._l10n_ca_param(code, day)

        rnd = self.currency_id.round
        taxable = rnd(
            self.amount * (1 + param(f"l10n_ca.dividend.fed.{kind}_gross_up"))
        )
        qc_taxable = rnd(
            self.amount * (1 + param(f"l10n_ca.dividend.qc.{kind}_gross_up"))
        )
        return {
            "taxable": taxable,
            "fed_credit": rnd(taxable * param(f"l10n_ca.dividend.fed.{kind}_credit")),
            "qc_taxable": qc_taxable,
            "qc_credit": rnd(qc_taxable * param(f"l10n_ca.dividend.qc.{kind}_credit")),
        }
