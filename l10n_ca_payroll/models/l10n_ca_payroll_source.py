# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.osv import expression

from ..tools.sources_page import PAYROLL_PREFIXES


class L10nCaPayrollSource(models.Model):
    """Official publication, page or statute behind the payroll figures.

    The records are data of the payroll modules, one file per jurisdiction,
    from which ``tools/sources_page.py`` also writes the static page
    ``static/description/sources.html``. A source is linked to the payroll
    time parameters (codes starting with ``PAYROLL_PREFIXES``) whose
    description cites its URL.
    """

    _name = "l10n_ca.payroll.source"
    _description = "Official Source of the Canadian Payroll"
    _order = "jurisdiction, sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    publisher = fields.Char(translate=True)
    jurisdiction = fields.Selection(
        [("federal", "Federal"), ("quebec", "Quebec"), ("ontario", "Ontario")],
        required=True,
    )
    kind = fields.Selection(
        [
            ("publication", "Publication"),
            ("page", "Web Page"),
            ("statute", "Statute or Regulation"),
        ],
        required=True,
        default="publication",
    )
    reference = fields.Char(
        help="Edition, table, part or section of the source that the payroll relies on."
    )
    url = fields.Char(string="URL", required=True)
    summary = fields.Text(
        translate=True, help="Figures and rules of the payroll that come from it."
    )
    state = fields.Selection(
        [("verified", "Verified"), ("to_verify", "To Verify")],
        string="Verification",
        required=True,
        default="verified",
        help="To Verify: the official text could not be read automatically; "
        "the note says what to confirm in a browser.",
    )
    verification_note = fields.Text(translate=True)
    verified_date = fields.Date(
        help="Date the figures were last compared with the official text."
    )
    parameter_ids = fields.Many2many(
        "base.time.parameter",
        string="Time Parameters",
        compute="_compute_parameter_ids",
        help="Time parameters whose description cites the URL of the source.",
    )
    parameter_count = fields.Integer(compute="_compute_parameter_ids")

    @api.depends("url")
    def _compute_parameter_ids(self):
        Parameter = self.env["base.time.parameter"]
        for source in self:
            parameters = Parameter.browse()
            if source.url:
                prefixes = expression.OR(
                    [[("code", "=like", f"{prefix}%")] for prefix in PAYROLL_PREFIXES]
                )
                parameters = Parameter.search(
                    expression.AND([[("description", "ilike", source.url)], prefixes]),
                    order="code",
                )
            source.parameter_ids = parameters
            source.parameter_count = len(parameters)
