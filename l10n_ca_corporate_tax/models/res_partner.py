# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ca_shareholder = fields.Boolean(
        string="Shareholder",
        help="Shareholder of the company: recipient of dividends and "
        "subject to the shareholder loan rules.",
    )
    l10n_ca_related_person = fields.Boolean(
        string="Connected to a Shareholder",
        help="Person connected with a shareholder (ITA s. 15(2.1)), such as "
        "a spouse or a child: loans to this person follow the shareholder "
        "loan rules.",
    )
