# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

GIFI_MAPPING_SOURCES = [
    ("account", "Account"),
    ("type", "Account type fallback"),
    ("none", "Unmapped"),
]


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_ca_gifi_code_id = fields.Many2one(
        "l10n.ca.gifi.code",
        string="GIFI Code",
        ondelete="restrict",
        index="btree_not_null",
        domain=[("is_total", "=", False)],
        help="Item of the General Index of Financial Information where the "
        "balance of this account is reported (T2 schedules 100 and 125). "
        "Empty: the code set for the account type is used.",
    )
    l10n_ca_gifi_effective_code_id = fields.Many2one(
        "l10n.ca.gifi.code",
        string="Effective GIFI Code",
        compute="_compute_l10n_ca_gifi",
    )
    l10n_ca_gifi_mapping = fields.Selection(
        GIFI_MAPPING_SOURCES,
        string="GIFI Mapping",
        compute="_compute_l10n_ca_gifi",
        search="_search_l10n_ca_gifi_mapping",
    )

    @api.constrains("l10n_ca_gifi_code_id")
    def _check_l10n_ca_gifi_code(self):
        if self.l10n_ca_gifi_code_id.filtered("is_total"):
            raise ValidationError(
                _("A computed GIFI total cannot be mapped to an account.")
            )

    @api.depends("l10n_ca_gifi_code_id", "account_type")
    @api.depends_context("company")
    def _compute_l10n_ca_gifi(self):
        codes = self._l10n_ca_gifi_code_map(self.env.company)
        for account in self:
            code, source = codes[account]
            account.l10n_ca_gifi_effective_code_id = code
            account.l10n_ca_gifi_mapping = source

    def _search_l10n_ca_gifi_mapping(self, operator, value):
        if operator not in ("=", "in"):
            raise UserError(_("Unsupported search on the GIFI mapping."))
        values = [value] if operator == "=" else list(value)
        mapped_types = list(
            self.env["l10n.ca.gifi.account.type.map"]._get_type_map(self.env.company)
        )
        domains = {
            "account": [("l10n_ca_gifi_code_id", "!=", False)],
            "type": [
                ("l10n_ca_gifi_code_id", "=", False),
                ("account_type", "in", mapped_types),
            ],
            "none": [
                ("l10n_ca_gifi_code_id", "=", False),
                ("account_type", "not in", mapped_types + ["off_balance"]),
            ],
        }
        # Each source is a conjunction of leaves: OR them as whole domains.
        return expression.OR([domains[source] for source in values])

    def _l10n_ca_gifi_code_map(self, company):
        """Return ``{account: (gifi.code, source)}`` for ``company``.

        ``source`` is ``account`` for a code set on the account, ``type``
        for the fallback of its account type, ``none`` when neither
        applies; off-balance accounts are never reported and stay
        ``none`` with an empty code.
        """
        type_map = self.env["l10n.ca.gifi.account.type.map"]._get_type_map(company)
        empty = self.env["l10n.ca.gifi.code"]
        result = {}
        for account in self:
            if account.l10n_ca_gifi_code_id:
                result[account] = (account.l10n_ca_gifi_code_id, "account")
            elif account.account_type in type_map:
                result[account] = (type_map[account.account_type], "type")
            else:
                result[account] = (empty, "none")
        return result
