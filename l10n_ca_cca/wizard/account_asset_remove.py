# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class AccountAssetRemove(models.TransientModel):
    _inherit = "account.asset.remove"

    def remove(self):
        """Copy the sale value to the proceeds of disposition of the asset.

        The removal date reaches the CCA disposition date through the
        computed field on ``date_remove``.
        """
        result = super().remove()
        asset = self.env["account.asset"].browse(self.env.context.get("active_id"))
        if asset.l10n_ca_cca_class_id:
            asset.l10n_ca_cca_proceeds = self.sale_value
        return result
