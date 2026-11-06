# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

GIFI_CATEGORIES = [
    ("asset", "Assets"),
    ("liability", "Liabilities"),
    ("equity", "Equity"),
    ("retained_earnings", "Retained Earnings"),
    ("other_comprehensive_income", "Other Comprehensive Income"),
    ("revenue", "Revenue"),
    ("cost_of_sales", "Cost of Sales"),
    ("expense", "Operating Expenses"),
    ("farm_revenue", "Farming Revenue"),
    ("farm_expense", "Farming Expenses"),
    ("extraordinary", "Extraordinary Items and Income Taxes"),
]

_FORMULA_TERM = re.compile(r"([+-])(\d{4})")


class L10nCaGifiCode(models.Model):
    """One item of the CRA General Index of Financial Information.

    Detail items receive account balances. Totals (``is_total``) are
    computed: a total is the signed sum of the items whose ``total_id``
    points to it, or the value of ``formula`` when the item belongs to
    no single block (8519 is 8089 minus 8518 while 8089 already rolls
    into 8299). Amounts follow the sign convention of the schedules:
    an item is positive when its account balance is on the side of
    ``normal_balance``; contra items such as accumulated amortization
    keep the asset side and come out negative.
    """

    _name = "l10n.ca.gifi.code"
    _description = "GIFI Code"
    _order = "code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(required=True, size=4, index=True)
    name = fields.Char(required=True, translate=True)
    category = fields.Selection(GIFI_CATEGORIES, required=True)
    schedule = fields.Selection(
        [
            ("100", "Schedule 100 - Balance Sheet"),
            ("125", "Schedule 125 - Income Statement"),
        ],
        required=True,
        help="Schedule 101, the opening balance sheet of the first year, "
        "uses the codes of Schedule 100.",
    )
    is_total = fields.Boolean(
        string="Total",
        help="Computed from other items; no account can be mapped to it.",
    )
    normal_balance = fields.Selection(
        [("debit", "Debit"), ("credit", "Credit")],
        required=True,
        default="debit",
        help="Side of the account balance reported as a positive amount.",
    )
    total_id = fields.Many2one(
        "l10n.ca.gifi.code",
        string="Rolls Into",
        ondelete="restrict",
        help="Total that includes this item.",
    )
    total_sign = fields.Integer(
        default=1,
        help="1 when the item is added to its total, -1 when it is "
        "subtracted (closing inventory, dividends, income taxes).",
    )
    component_ids = fields.One2many(
        "l10n.ca.gifi.code", "total_id", string="Components"
    )
    parent_id = fields.Many2one(
        "l10n.ca.gifi.code",
        string="Lead Item",
        ondelete="restrict",
        help="Generic item, printed in bold in guide RC4088, that heads "
        "the block of this item. The GIFI-Short groups a block under it.",
    )
    formula = fields.Char(
        help="Signed codes, such as '+8089 -8518', for a calculated item "
        "that is not the sum of one block.",
    )
    expected_sign = fields.Selection(
        [
            ("positive", "Positive"),
            ("negative", "Negative"),
            ("any", "Any"),
        ],
        default="positive",
        required=True,
        help="Sign of a normal amount; the GIFI statement warns about "
        "an amount of the other sign.",
    )
    partnership_only = fields.Boolean(
        help="Item reserved to partnerships (T5013); not used on a T2."
    )
    required = fields.Boolean(
        string="Required Item",
        help="Item that must be reported, even when nil (RC4088, "
        "Validity check items).",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "A GIFI code must be unique."),
    ]

    @api.constrains("code")
    def _check_code(self):
        for record in self:
            if not re.fullmatch(r"\d{4}", record.code or ""):
                raise ValidationError(
                    _("A GIFI code has exactly four digits: %s", record.code)
                )

    @api.constrains("total_sign")
    def _check_total_sign(self):
        if any(record.total_sign not in (1, -1) for record in self):
            raise ValidationError(_("The total sign is 1 or -1."))

    @api.constrains("formula")
    def _check_formula(self):
        for record in self.filtered("formula"):
            if _FORMULA_TERM.sub("", record.formula).strip():
                raise ValidationError(
                    _(
                        "Invalid formula '%s': use signed four-digit codes "
                        "such as '+8089 -8518'.",
                        record.formula,
                    )
                )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} {record.name or ''}".strip()

    def _formula_terms(self):
        """Return the ``(sign, code)`` pairs of ``formula``."""
        self.ensure_one()
        return [
            (1 if sign == "+" else -1, code)
            for sign, code in _FORMULA_TERM.findall(self.formula or "")
        ]

    def _amount_sign(self):
        """Return the factor that turns a debit-minus-credit balance into
        the amount reported for this item."""
        self.ensure_one()
        return 1 if self.normal_balance == "debit" else -1
