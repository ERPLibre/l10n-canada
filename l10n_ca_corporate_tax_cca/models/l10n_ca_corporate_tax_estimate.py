# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, models
from odoo.tools import format_amount

from odoo.addons.l10n_ca_corporate_tax.models.l10n_ca_corporate_tax_estimate import (
    PL_ACCOUNT_TYPES,
)

# Tax treatments whose accounts the corporate tax module already adds back
# in full: a depreciation entry posted to them is not added back twice.
ADDED_BACK_TREATMENTS = ("meals", "non_deductible")


class L10nCaCorporateTaxEstimate(models.Model):
    _inherit = "l10n.ca.corporate.tax.estimate"

    def _l10n_ca_cca_schedule(self, jurisdiction="federal"):
        """Return the CCA schedule of ``jurisdiction`` ending with the fiscal year.

        A CCA schedule is unique per company, jurisdiction and end date, so
        the end date alone identifies the schedule of the same year.
        """
        self.ensure_one()
        return self.env["l10n.ca.cca.schedule"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("jurisdiction", "=", jurisdiction),
                ("date_to", "=", self.date_to),
            ],
            limit=1,
        )

    def _l10n_ca_cca_schedule_items(self, schedule):
        """Return the Schedule 1 items of ``schedule`` as ``(label, amount)``.

        ``amount`` is signed like an estimate adjustment: positive is added
        to accounting income, negative is deducted. Book depreciation is
        not an item: it comes from the ledger (see
        ``_l10n_ca_asset_depreciation_not_added_back``).
        """
        return [
            (_("Capital cost allowance claimed (line 403)"), -schedule.total_cca),
            (
                _("Recapture of capital cost allowance (line 107)"),
                schedule.total_recapture,
            ),
            (_("Terminal loss (line 404)"), -schedule.total_terminal_loss),
            (
                _("Book gain on disposal of assets reversed (line 401)"),
                -schedule.total_book_gain,
            ),
            (
                _("Book loss on disposal of assets reversed (line 111)"),
                schedule.total_book_loss,
            ),
        ]

    def _l10n_ca_cca_net_adjustment(self, schedule):
        return sum(
            amount for _label, amount in self._l10n_ca_cca_schedule_items(schedule)
        )

    def _l10n_ca_get_cca_adjustments(self):
        """Add the non-zero Schedule 1 items of the federal CCA schedule."""
        adjustments = super()._l10n_ca_get_cca_adjustments()
        schedule = self._l10n_ca_cca_schedule("federal")
        if not schedule:
            return adjustments
        for label, amount in self._l10n_ca_cca_schedule_items(schedule):
            if self.currency_id.is_zero(amount):
                continue
            adjustments.append(
                {
                    "name": _(
                        "%(item)s - %(schedule)s", item=label, schedule=schedule.name
                    ),
                    "amount": amount,
                }
            )
        return adjustments

    def _l10n_ca_asset_depreciation_not_added_back(self):
        """Return the asset depreciation of the year missed by the base add-back.

        Sums the posted depreciation entries of the company's assets, dated
        in the fiscal year, on the profit and loss accounts that the
        corporate tax module does not add back already: accounts that are
        not of type *Depreciation* and carry no meals or non-deductible tax
        treatment. Reading the ledger keeps the add-back consistent with the
        accounting income of the estimate.
        """
        self.ensure_one()
        asset_lines = self.env["account.asset.line"].search(
            [
                ("asset_id.company_id", "=", self.company_id.id),
                ("type", "=", "depreciate"),
                ("move_id.state", "=", "posted"),
                ("move_id.date", ">=", self.date_from),
                ("move_id.date", "<=", self.date_to),
            ]
        )
        if not asset_lines:
            return 0.0
        groups = self.env["account.move.line"]._read_group(
            [
                ("move_id", "in", asset_lines.move_id.ids),
                ("account_id.account_type", "in", PL_ACCOUNT_TYPES),
            ],
            ["account_id"],
            ["balance:sum"],
        )
        return sum(
            balance
            for account, balance in groups
            if account.account_type != "expense_depreciation"
            and account.l10n_ca_tax_treatment not in ADDED_BACK_TREATMENTS
        )

    def _l10n_ca_accounting_adjustments(self, balances):
        """Insert the missed asset depreciation before the CCA lines."""
        values = super()._l10n_ca_accounting_adjustments(balances)
        amount = self._l10n_ca_asset_depreciation_not_added_back()
        if self.currency_id.is_zero(amount):
            return values
        index = next(
            (i for i, vals in enumerate(values) if vals["adjustment_type"] == "cca"),
            len(values),
        )
        values.insert(
            index,
            {
                "adjustment_type": "depreciation",
                "name": _("Book depreciation of assets in other expense accounts"),
                "amount": amount,
            },
        )
        return values

    def _l10n_ca_cca_warnings(self):
        """Return the warnings about the CCA schedules of the fiscal year."""
        self.ensure_one()
        currency = self.currency_id
        warnings = []
        federal = self._l10n_ca_cca_schedule("federal")
        if not federal:
            has_assets = self.env["account.asset"].search_count(
                [
                    ("company_id", "=", self.company_id.id),
                    ("l10n_ca_cca_class_id", "!=", False),
                    ("state", "!=", "draft"),
                ],
                limit=1,
            )
            if has_assets:
                warnings.append(
                    _(
                        "No federal CCA schedule ends on %(date)s: the capital "
                        "cost allowance is not loaded from the assets.",
                        date=self.date_to,
                    )
                )
            return warnings
        federal_net = self._l10n_ca_cca_net_adjustment(federal)
        if self.adjustment_ids.filtered("auto"):
            loaded = sum(
                self.adjustment_ids.filtered(
                    lambda line: line.auto and line.adjustment_type == "cca"
                ).mapped("amount")
            )
            if currency.compare_amounts(loaded, federal_net):
                warnings.append(
                    _(
                        "The CCA lines loaded (%(loaded)s) differ from %(schedule)s "
                        "(%(expected)s): click Load from Accounting again.",
                        loaded=format_amount(self.env, loaded, currency),
                        schedule=federal.name,
                        expected=format_amount(self.env, federal_net, currency),
                    )
                )
        quebec = self._l10n_ca_cca_schedule("quebec")
        if quebec:
            difference = self._l10n_ca_cca_net_adjustment(quebec) - federal_net
            if not currency.is_zero(difference):
                warnings.append(
                    _(
                        "The Quebec CCA schedule gives a Quebec taxable income "
                        "%(difference)s different from the federal one (positive: "
                        "higher). The estimate computes both taxes on the federal "
                        "taxable income, so the Quebec tax is estimated on that "
                        "difference too.",
                        difference=format_amount(self.env, difference, currency),
                    )
                )
        return warnings

    def _l10n_ca_compute_values(self):
        values = super()._l10n_ca_compute_values()
        warnings = self._l10n_ca_cca_warnings()
        if warnings:
            values["warning_message"] = "\n".join(
                [values["warning_message"] or ""] + warnings
            )
        return values
