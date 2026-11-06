# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import csv
import datetime
import io
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# Column titles of the CSV and XLSX exports, translated with env._() at
# export time.
BOX_FIELDS = [
    ("t5_box_24", _lt("T5 box 24 - Actual amount of eligible dividends")),
    ("t5_box_25", _lt("T5 box 25 - Taxable amount of eligible dividends")),
    ("t5_box_26", _lt("T5 box 26 - Dividend tax credit for eligible dividends")),
    ("t5_box_10", _lt("T5 box 10 - Actual amount of other than eligible dividends")),
    ("t5_box_11", _lt("T5 box 11 - Taxable amount of other than eligible dividends")),
    (
        "t5_box_12",
        _lt("T5 box 12 - Dividend tax credit for other than eligible dividends"),
    ),
    ("rl3_box_a1", _lt("RL-3 box A1 - Actual amount of eligible dividends")),
    ("rl3_box_a2", _lt("RL-3 box A2 - Actual amount of ordinary dividends")),
    (
        "rl3_box_b",
        _lt("RL-3 box B - Taxable amount of eligible and ordinary dividends"),
    ),
    ("rl3_box_c", _lt("RL-3 box C - Dividend tax credit")),
]


class L10nCaDividendSlip(models.Model):
    _name = "l10n.ca.dividend.slip"
    _description = "T5 and RL-3 Dividend Slip Data"
    _order = "year desc, partner_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    year = fields.Integer(string="Calendar Year", required=True)
    partner_id = fields.Many2one("res.partner", string="Recipient", required=True)
    t5_required = fields.Boolean(
        string="T5 Required",
        help="False when the dividends paid to the recipient in the year are "
        "below the minimum amount of the T5 return.",
    )
    t5_box_24 = fields.Monetary(string="T5 Box 24")
    t5_box_25 = fields.Monetary(string="T5 Box 25")
    t5_box_26 = fields.Monetary(string="T5 Box 26")
    t5_box_10 = fields.Monetary(string="T5 Box 10")
    t5_box_11 = fields.Monetary(string="T5 Box 11")
    t5_box_12 = fields.Monetary(string="T5 Box 12")
    rl3_box_a1 = fields.Monetary(string="RL-3 Box A1")
    rl3_box_a2 = fields.Monetary(string="RL-3 Box A2")
    rl3_box_b = fields.Monetary(string="RL-3 Box B")
    rl3_box_c = fields.Monetary(string="RL-3 Box C")

    _sql_constraints = [
        (
            "l10n_ca_dividend_slip_unique",
            "unique (company_id, year, partner_id)",
            "One slip per recipient and year.",
        ),
    ]

    @api.model
    def _l10n_ca_generate(self, company, year):
        """Rebuild the slips of ``year`` from the paid dividends.

        Each dividend contributes its amounts computed at its payment date;
        the boxes are the sums per recipient. Returns the slips.
        """
        self.search([("company_id", "=", company.id), ("year", "=", year)]).unlink()
        dividends = self.env["l10n.ca.dividend"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "paid"),
                ("payment_date", ">=", datetime.date(year, 1, 1)),
                ("payment_date", "<=", datetime.date(year, 12, 31)),
            ]
        )
        totals = defaultdict(lambda: defaultdict(float))
        for dividend in dividends:
            amounts = dividend._l10n_ca_slip_amounts()
            box = totals[dividend.partner_id]
            if dividend.dividend_type == "eligible":
                box["t5_box_24"] += dividend.amount
                box["t5_box_25"] += amounts["taxable"]
                box["t5_box_26"] += amounts["fed_credit"]
                box["rl3_box_a1"] += dividend.amount
            else:
                box["t5_box_10"] += dividend.amount
                box["t5_box_11"] += amounts["taxable"]
                box["t5_box_12"] += amounts["fed_credit"]
                box["rl3_box_a2"] += dividend.amount
            box["rl3_box_b"] += amounts["qc_taxable"]
            box["rl3_box_c"] += amounts["qc_credit"]
        minimum = company._l10n_ca_param(
            "l10n_ca.dividend.t5_min_amount", datetime.date(year, 12, 31)
        )
        slips = self.browse()
        for partner, box in totals.items():
            values = {
                name: company.currency_id.round(box[name]) for name, _l in BOX_FIELDS
            }
            values.update(
                company_id=company.id,
                year=year,
                partner_id=partner.id,
                t5_required=box["t5_box_24"] + box["t5_box_10"] >= minimum,
            )
            slips |= self.create(values)
        return slips

    def _l10n_ca_summary(self):
        """Return the summary totals: slip count and one total per box."""
        summary = {name: sum(self.mapped(name)) for name, _l in BOX_FIELDS}
        summary["t5_count"] = len(self.filtered("t5_required"))
        summary["rl3_count"] = len(self)
        return summary

    def _l10n_ca_csv(self):
        """Return the slips as CSV text, one row per recipient.

        The columns follow the boxes of the CRA T5 web form and of the
        Revenu Quebec RL-3 online service; the recipient's social insurance
        number is entered in those forms, it is not stored here.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        header = [
            _("Year"),
            _("Recipient"),
            _("Street"),
            _("City"),
            _("Province"),
            _("Postal Code"),
            _("T5 Required"),
        ] + [self.env._(label) for _n, label in BOX_FIELDS]
        writer.writerow(header)
        for slip in self:
            partner = slip.partner_id
            writer.writerow(
                [
                    slip.year,
                    partner.name or "",
                    " ".join(filter(None, [partner.street, partner.street2])),
                    partner.city or "",
                    partner.state_id.code or "",
                    partner.zip or "",
                    _("Yes") if slip.t5_required else _("No"),
                ]
                + [f"{slip[name]:.2f}" for name, _l in BOX_FIELDS]
            )
        summary = self._l10n_ca_summary()
        writer.writerow(
            [_("Total"), "", "", "", "", "", summary["t5_count"]]
            + [f"{summary[name]:.2f}" for name, _l in BOX_FIELDS]
        )
        return output.getvalue()
