# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountAssetProfile(models.Model):
    _inherit = "account.asset.profile"

    l10n_ca_cca_class_id = fields.Many2one(
        "l10n.ca.cca.class",
        string="CCA Class",
        help="Default capital cost allowance class of the assets of this profile.",
    )
