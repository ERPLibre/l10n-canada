# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nCaGifiAccountTypeMap(models.Model):
    """GIFI code used for an account that has no code of its own.

    A row of a company wins over a row without company for the same
    account type.
    """

    _name = "l10n.ca.gifi.account.type.map"
    _description = "GIFI Code by Account Type"
    _order = "account_type, company_id"

    account_type = fields.Selection(selection="_selection_account_type", required=True)
    gifi_code_id = fields.Many2one(
        "l10n.ca.gifi.code",
        string="GIFI Code",
        required=True,
        ondelete="restrict",
        domain=[("is_total", "=", False)],
    )
    company_id = fields.Many2one(
        "res.company",
        help="Leave empty to apply the row to every company.",
    )

    @api.model
    def _selection_account_type(self):
        """Account types of ``account.account``, labels in the user's
        language: a selection given by a method is not translated by the
        ORM, unlike the static selection it copies."""
        field = self.env["account.account"]._fields["account_type"]
        return field._description_selection(self.env)

    @api.constrains("account_type", "company_id")
    def _check_unique_type(self):
        for record in self:
            duplicate = self.search_count(
                [
                    ("id", "!=", record.id),
                    ("account_type", "=", record.account_type),
                    ("company_id", "=", record.company_id.id),
                ]
            )
            if duplicate:
                raise ValidationError(
                    _("An account type has one fallback GIFI code per company.")
                )

    @api.constrains("gifi_code_id")
    def _check_not_total(self):
        if self.gifi_code_id.filtered("is_total"):
            raise ValidationError(_("A computed GIFI total cannot be mapped."))

    @api.model
    def _get_type_map(self, company):
        """Return ``{account_type: gifi.code}`` in force for ``company``."""
        rows = self.sudo().search([("company_id", "in", (company.id, False))])
        result = {}
        # Rows without company first, so that a company row overrides them.
        for row in rows.sorted(lambda r: bool(r.company_id)):
            result[row.account_type] = row.gifi_code_id
        return result
