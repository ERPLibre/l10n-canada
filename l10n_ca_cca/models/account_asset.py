# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    l10n_ca_cca_class_id = fields.Many2one(
        "l10n.ca.cca.class",
        string="CCA Class",
        compute="_compute_l10n_ca_cca_class_id",
        store=True,
        readonly=False,
        help="Capital cost allowance class. Assets without a class are left "
        "out of the CCA schedules.",
    )
    l10n_ca_cca_acquisition_date = fields.Date(
        string="CCA Acquisition Date",
        compute="_compute_l10n_ca_cca_acquisition_date",
        store=True,
        readonly=False,
        help="Date the corporation acquired the property. Decides the "
        "prescribed cost limit and the incentive windows.",
    )
    l10n_ca_cca_available_date = fields.Date(
        string="Available-for-Use Date",
        compute="_compute_l10n_ca_cca_available_date",
        store=True,
        readonly=False,
        help="Date the property became available for use (ITA 13(26)-(31)). "
        "The capital cost enters the class in the taxation year that "
        "contains this date, at the latest in the second taxation year "
        "after the acquisition.",
    )
    l10n_ca_cca_capital_cost = fields.Monetary(
        string="CCA Capital Cost",
        compute="_compute_l10n_ca_cca_capital_cost",
        store=True,
        readonly=False,
        help="Cost added to the class: the purchase value, limited to the "
        "prescribed amount of the class (classes 10.1 and 54). Reduce it by "
        "government assistance or investment tax credits received.",
    )
    l10n_ca_cca_enhancement_excluded = fields.Boolean(
        string="Previously Owned or Non-Arm's Length",
        help="The property was owned before by the corporation or a person "
        "not dealing at arm's length, or was acquired on a rollover: it gets "
        "neither the accelerated investment incentive nor immediate "
        "expensing (Reg. 1104(4)).",
    )
    l10n_ca_cca_half_year_exempt = fields.Boolean(
        string="Exempt from Half-Year Rule",
        compute="_compute_l10n_ca_cca_half_year_exempt",
        store=True,
        readonly=False,
        help="Set when the cost is under the half-year exemption threshold of "
        "the class (class 12 small tools).",
    )
    l10n_ca_cca_immediate_expensing = fields.Boolean(
        string="Eligible for Immediate Expensing",
        compute="_compute_l10n_ca_cca_immediate_expensing",
        store=True,
        readonly=False,
        help="Set when the class and dates fall in an immediate expensing "
        "window, or in the CCPC designated immediate expensing window. Clear "
        "it to leave the asset under the normal rules.",
    )
    l10n_ca_cca_life_years = fields.Float(
        string="CCA Life (Years)",
        compute="_compute_l10n_ca_cca_life_years",
        store=True,
        readonly=False,
        help="Straight-line classes only: lease term plus first renewal "
        "(class 13) or legal life (class 14).",
    )
    l10n_ca_cca_disposal_date = fields.Date(
        string="CCA Disposition Date",
        compute="_compute_l10n_ca_cca_disposal_date",
        store=True,
        readonly=False,
    )
    l10n_ca_cca_proceeds = fields.Monetary(
        string="Proceeds of Disposition",
        help="Proceeds received on disposition. Filled from the sale value "
        "entered in the asset removal wizard.",
    )

    @api.depends("profile_id")
    def _compute_l10n_ca_cca_class_id(self):
        for asset in self:
            if asset.profile_id.l10n_ca_cca_class_id:
                asset.l10n_ca_cca_class_id = asset.profile_id.l10n_ca_cca_class_id

    # One compute method per date: Odoo protects every field of a method
    # when one of them is given at creation, which would leave the other
    # date empty.
    @api.depends("date_start")
    def _compute_l10n_ca_cca_acquisition_date(self):
        for asset in self:
            asset.l10n_ca_cca_acquisition_date = asset.date_start

    @api.depends("date_start")
    def _compute_l10n_ca_cca_available_date(self):
        for asset in self:
            asset.l10n_ca_cca_available_date = asset.date_start

    @api.depends("date_remove")
    def _compute_l10n_ca_cca_disposal_date(self):
        for asset in self:
            asset.l10n_ca_cca_disposal_date = asset.date_remove

    @api.depends(
        "purchase_value", "l10n_ca_cca_class_id", "l10n_ca_cca_acquisition_date"
    )
    def _compute_l10n_ca_cca_capital_cost(self):
        for asset in self:
            cost = asset.purchase_value
            cca_class = asset.l10n_ca_cca_class_id
            if cca_class and asset.l10n_ca_cca_acquisition_date:
                limit = cca_class._param(
                    "cost_limit", asset.l10n_ca_cca_acquisition_date, asset.company_id
                )
                if limit is not None:
                    cost = min(cost, limit)
            asset.l10n_ca_cca_capital_cost = cost

    @api.depends(
        "l10n_ca_cca_class_id",
        "l10n_ca_cca_capital_cost",
        "l10n_ca_cca_acquisition_date",
    )
    def _compute_l10n_ca_cca_half_year_exempt(self):
        for asset in self:
            exempt = False
            cca_class = asset.l10n_ca_cca_class_id
            if cca_class and asset.l10n_ca_cca_acquisition_date:
                threshold = cca_class._param(
                    "half_year_exempt_below",
                    asset.l10n_ca_cca_acquisition_date,
                    asset.company_id,
                )
                exempt = threshold is not None and (
                    asset.l10n_ca_cca_capital_cost < threshold
                )
            asset.l10n_ca_cca_half_year_exempt = exempt

    @api.depends(
        "l10n_ca_cca_class_id",
        "l10n_ca_cca_acquisition_date",
        "l10n_ca_cca_available_date",
        "l10n_ca_cca_enhancement_excluded",
        "company_id.l10n_ca_ccpc",
    )
    def _compute_l10n_ca_cca_immediate_expensing(self):
        for asset in self:
            asset.l10n_ca_cca_immediate_expensing = bool(
                asset._l10n_ca_cca_expensing_rate()
            )

    @api.depends("l10n_ca_cca_class_id", "method_number")
    def _compute_l10n_ca_cca_life_years(self):
        for asset in self:
            if asset.l10n_ca_cca_class_id.method == "straight_line":
                asset.l10n_ca_cca_life_years = (
                    asset.l10n_ca_cca_life_years or asset.method_number
                )
            else:
                asset.l10n_ca_cca_life_years = 0.0

    def _l10n_ca_cca_expensing_rate(self, date=None, jurisdiction="federal"):
        """Return the immediate expensing rate of the asset as an addition.

        The class window wins; the CCPC designation applies only when the
        class has no window for these dates. ``date`` selects the parameter
        versions, the available-for-use date by default. Returns 0.0 when
        the asset is excluded or no window matches.
        """
        self.ensure_one()
        cca_class = self.l10n_ca_cca_class_id
        acquired = self.l10n_ca_cca_acquisition_date
        available = self.l10n_ca_cca_available_date
        if not cca_class or not available or self.l10n_ca_cca_enhancement_excluded:
            return 0.0
        date = date or available
        company = self.company_id
        return cca_class._expensing_rate(
            company, acquired, available, date, jurisdiction
        ) or cca_class._diep_rate(company, acquired, available, date, jurisdiction)
