# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import cca_param

# Reg. 1100(3): the allowance of a taxation year shorter than this number of
# days is prorated by its number of days.
DAYS_IN_YEAR = 365

JURISDICTIONS = [
    ("federal", "Federal (T2 Schedule 8)"),
    ("quebec", "Quebec (CO-17)"),
]


class L10nCaCcaSchedule(models.Model):
    """Capital cost allowance schedule of one taxation year.

    Lines are generated from the assets of ``account_asset_management``:
    the opening balance of each class comes from the closing balance of the
    previous schedule of the same company and jurisdiction, so locking the
    schedules year after year carries the undepreciated capital cost
    forward.
    """

    _name = "l10n.ca.cca.schedule"
    _description = "Capital Cost Allowance Schedule"
    _order = "date_to desc, jurisdiction"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    jurisdiction = fields.Selection(JURISDICTIONS, required=True, default="federal")
    date_from = fields.Date(
        string="Taxation Year Start",
        required=True,
        default=lambda self: self._default_fiscal_dates()["date_from"],
    )
    date_to = fields.Date(
        string="Taxation Year End",
        required=True,
        default=lambda self: self._default_fiscal_dates()["date_to"],
    )
    state = fields.Selection(
        [("draft", "Draft"), ("locked", "Locked")],
        default="draft",
        required=True,
        copy=False,
    )
    line_ids = fields.One2many(
        "l10n.ca.cca.schedule.line", "schedule_id", string="Classes", copy=False
    )
    previous_id = fields.Many2one(
        "l10n.ca.cca.schedule",
        string="Previous Schedule",
        compute="_compute_previous_id",
    )
    note = fields.Text()

    total_opening_ucc = fields.Monetary(compute="_compute_totals", store=True)
    total_additions = fields.Monetary(compute="_compute_totals", store=True)
    total_dispositions = fields.Monetary(compute="_compute_totals", store=True)
    total_max_cca = fields.Monetary(
        string="Total Maximum CCA", compute="_compute_totals", store=True
    )
    total_cca = fields.Monetary(
        string="Total CCA Claimed",
        compute="_compute_totals",
        store=True,
        help="Deducted on line 403 of T2 Schedule 1.",
    )
    total_recapture = fields.Monetary(
        compute="_compute_totals",
        store=True,
        help="Added on line 107 of T2 Schedule 1.",
    )
    total_terminal_loss = fields.Monetary(
        compute="_compute_totals",
        store=True,
        help="Deducted on line 404 of T2 Schedule 1.",
    )
    total_closing_ucc = fields.Monetary(compute="_compute_totals", store=True)
    total_book_depreciation = fields.Monetary(
        compute="_compute_totals",
        store=True,
        help="Book amortization of the year, added back on line 104 of T2 "
        "Schedule 1.",
    )
    total_book_gain = fields.Monetary(
        string="Book Gain on Disposals",
        compute="_compute_totals",
        store=True,
        help="Gain on disposal of assets in the financial statements, "
        "deducted on line 401 of T2 Schedule 1.",
    )
    total_book_loss = fields.Monetary(
        string="Book Loss on Disposals",
        compute="_compute_totals",
        store=True,
        help="Loss on disposal of assets in the financial statements, added "
        "on line 111 of T2 Schedule 1.",
    )
    total_capital_gain = fields.Monetary(
        compute="_compute_totals",
        store=True,
        help="Proceeds in excess of the capital cost, to report on T2 Schedule 6.",
    )
    schedule1_adjustment = fields.Monetary(
        string="Net Schedule 1 Adjustment",
        compute="_compute_totals",
        store=True,
        help="Book amortization + recapture + book loss - book gain - CCA - "
        "terminal loss. Positive: taxable income is higher than book income.",
    )

    _sql_constraints = [
        (
            "year_unique",
            "unique(company_id, jurisdiction, date_to)",
            "A CCA schedule already exists for this year and jurisdiction.",
        ),
        (
            "dates_order",
            "check(date_from <= date_to)",
            "The taxation year must end after it starts.",
        ),
    ]

    @api.model
    def _default_fiscal_dates(self):
        return self.env.company.compute_fiscalyear_dates(
            fields.Date.context_today(self)
        )

    @api.depends("jurisdiction", "date_to")
    def _compute_name(self):
        # Labels in the user's language: the name is stored, and the
        # untranslated JURISDICTIONS would mix English into a French name.
        labels = dict(self._fields["jurisdiction"]._description_selection(self.env))
        for schedule in self:
            schedule.name = _(
                "CCA %(year)s - %(jurisdiction)s",
                year=schedule.date_to and schedule.date_to.year or "",
                jurisdiction=labels.get(schedule.jurisdiction, ""),
            )

    @api.depends("company_id", "jurisdiction", "date_from")
    def _compute_previous_id(self):
        for schedule in self:
            schedule.previous_id = schedule._get_previous()

    def _get_previous(self):
        self.ensure_one()
        if not self.date_from:
            return self.browse()
        return self.search(
            [
                ("company_id", "=", self.company_id.id),
                ("jurisdiction", "=", self.jurisdiction),
                ("date_to", "<", self.date_from),
                ("id", "!=", self._origin.id or 0),
            ],
            order="date_to desc",
            limit=1,
        )

    @api.depends(
        "line_ids.opening_ucc",
        "line_ids.additions",
        "line_ids.dispositions",
        "line_ids.max_cca",
        "line_ids.cca_claimed",
        "line_ids.recapture",
        "line_ids.terminal_loss",
        "line_ids.closing_ucc",
        "line_ids.book_depreciation",
        "line_ids.book_gain_loss",
        "line_ids.capital_gain",
    )
    def _compute_totals(self):
        for schedule in self:
            lines = schedule.line_ids
            gains = lines.mapped("book_gain_loss")
            schedule.update(
                {
                    "total_opening_ucc": sum(lines.mapped("opening_ucc")),
                    "total_additions": sum(lines.mapped("additions")),
                    "total_dispositions": sum(lines.mapped("dispositions")),
                    "total_max_cca": sum(lines.mapped("max_cca")),
                    "total_cca": sum(lines.mapped("cca_claimed")),
                    "total_recapture": sum(lines.mapped("recapture")),
                    "total_terminal_loss": sum(lines.mapped("terminal_loss")),
                    "total_closing_ucc": sum(lines.mapped("closing_ucc")),
                    "total_book_depreciation": sum(lines.mapped("book_depreciation")),
                    "total_book_gain": sum(g for g in gains if g > 0),
                    "total_book_loss": -sum(g for g in gains if g < 0),
                    "total_capital_gain": sum(lines.mapped("capital_gain")),
                }
            )
            schedule.schedule1_adjustment = (
                schedule.total_book_depreciation
                + schedule.total_recapture
                + schedule.total_book_loss
                - schedule.total_book_gain
                - schedule.total_cca
                - schedule.total_terminal_loss
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_generate(self):
        for schedule in self:
            if schedule.state != "draft":
                raise UserError(_("Only a draft schedule can be generated."))
            schedule._generate_lines()
        return True

    def action_claim_maximum(self):
        for schedule in self:
            if schedule.state != "draft":
                raise UserError(_("The schedule %s is locked.", schedule.name))
            for line in schedule.line_ids:
                line.cca_claimed = line.max_cca
        return True

    def action_lock(self):
        for schedule in self:
            if not schedule.line_ids:
                raise UserError(_("Generate the schedule before locking it."))
            schedule.line_ids._check_cca_claimed()
        self.write({"state": "locked"})
        return True

    def action_unlock(self):
        for schedule in self:
            later = self.search(
                [
                    ("company_id", "=", schedule.company_id.id),
                    ("jurisdiction", "=", schedule.jurisdiction),
                    ("date_from", ">", schedule.date_to),
                    ("state", "=", "locked"),
                ],
                limit=1,
            )
            if later:
                raise UserError(
                    _(
                        "Unlock %(later)s first: its opening balances come "
                        "from this schedule.",
                        later=later.name,
                    )
                )
        self.write({"state": "draft"})
        return True

    def action_print(self):
        return self.env.ref("l10n_ca_cca.action_report_cca_schedule").report_action(
            self
        )

    def unlink(self):
        if any(schedule.state == "locked" for schedule in self):
            raise UserError(_("A locked CCA schedule cannot be deleted."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _param(self, key, default=None):
        self.ensure_one()
        return cca_param(
            self.company_id, key, self.date_to, self.jurisdiction, default=default
        )

    def _proration(self):
        days = (self.date_to - self.date_from).days + 1
        return min(1.0, days / DAYS_IN_YEAR)

    def _generate_lines(self):
        """Rebuild the lines from the previous schedule and the assets.

        Opening balances come from the previous schedule; without one, the
        opening balances typed on the current lines are kept, which is how
        the first year is started. Manual adjustments are kept. The CCA
        claimed is reset to the maximum.
        """
        self.ensure_one()
        context = {
            "half_year_factor": cca_param(
                self.company_id, "half_year_factor", self.date_to, self.jurisdiction
            ),
            "proration": self._proration(),
            "diep_left": None,
        }
        buckets = {}
        previous = self._get_previous()
        existing = {
            (line.class_id.id, line.asset_id.id or False): line
            for line in self.line_ids
        }
        if previous:
            for prev_line in previous.line_ids:
                if not prev_line.property_remaining:
                    continue
                bucket = self._bucket(buckets, prev_line.class_id, prev_line.asset_id)
                bucket["opening_ucc"] = prev_line.closing_ucc
        for (_class_id, _asset_id), line in existing.items():
            if not previous or line.adjustments:
                bucket = self._bucket(buckets, line.class_id, line.asset_id)
                if not previous:
                    bucket["opening_ucc"] = line.opening_ucc
                bucket["adjustments"] = line.adjustments

        assets = self.env["account.asset"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("l10n_ca_cca_class_id", "!=", False),
                ("state", "!=", "draft"),
                ("l10n_ca_cca_available_date", "<=", self.date_to),
            ]
        )
        classes_with_assets = assets.mapped("l10n_ca_cca_class_id")
        for asset in assets.sorted(lambda a: (a.l10n_ca_cca_available_date, a.id)):
            disposal = asset.l10n_ca_cca_disposal_date
            if disposal and disposal < self.date_from:
                continue
            bucket = self._bucket(buckets, asset.l10n_ca_cca_class_id, asset)
            self._add_asset(bucket, asset, context)

        self.line_ids.unlink()
        vals_list = []
        for bucket in buckets.values():
            vals = self._bucket_vals(bucket, context, classes_with_assets)
            if vals:
                vals_list.append(vals)
        lines = self.env["l10n.ca.cca.schedule.line"].create(vals_list)
        for line in lines:
            line.cca_claimed = line.max_cca
        return lines

    def _bucket(self, buckets, cca_class, asset):
        """Return the accumulator of a class, or of an asset in its own class."""
        asset_id = asset.id if cca_class.separate_class and asset else False
        key = (cca_class.id, asset_id)
        if key not in buckets:
            buckets[key] = {
                "class": cca_class,
                "asset_id": asset_id,
                "opening_ucc": 0.0,
                "adjustments": 0.0,
                "additions_regular": 0.0,
                "regular_base": 0.0,
                "additions_enhanced": 0.0,
                "enhanced_base": 0.0,
                "additions_expensing": 0.0,
                "expensing_allowance": 0.0,
                "straight_line_amount": 0.0,
                "dispositions": 0.0,
                "capital_gain": 0.0,
                "book_depreciation": 0.0,
                "book_gain_loss": 0.0,
                "assets_seen": False,
                "assets_remaining": False,
            }
        return buckets[key]

    def _add_asset(self, bucket, asset, context):
        """Accumulate one asset into its class for this taxation year."""
        date_from, date_to = self.date_from, self.date_to
        cca_class = asset.l10n_ca_cca_class_id
        disposal = asset.l10n_ca_cca_disposal_date
        disposed = bool(disposal and disposal <= date_to)
        bucket["assets_seen"] = True
        if not disposed:
            bucket["assets_remaining"] = True
        cost = asset.l10n_ca_cca_capital_cost
        if asset.l10n_ca_cca_available_date >= date_from:
            self._add_addition(bucket, asset, cost, context)
        elif cca_class.method == "straight_line" and not disposed:
            bucket["straight_line_amount"] += self._straight_line_annual(asset, cost)
        if disposed:
            proceeds = asset.l10n_ca_cca_proceeds
            tax_proceeds = proceeds
            if 0 < cost < asset.purchase_value:
                # ITA 13(2) and 13(7)(i): proceeds of a vehicle whose cost is
                # limited are reduced in the same proportion.
                tax_proceeds = proceeds * cost / asset.purchase_value
            bucket["dispositions"] += min(cost, tax_proceeds)
            bucket["capital_gain"] += max(0.0, proceeds - asset.purchase_value)
            removal = asset.depreciation_line_ids.filtered(
                lambda line: line.type == "remove"
                and date_from <= line.line_date <= date_to
            )
            if removal:
                bucket["book_gain_loss"] += proceeds - sum(removal.mapped("amount"))
        bucket["book_depreciation"] += sum(
            asset.depreciation_line_ids.filtered(
                lambda line: line.type == "depreciate"
                and (line.move_check or line.init_entry)
                and date_from <= line.line_date <= date_to
            ).mapped("amount")
        )

    def _first_year_factor(self, asset, context):
        """Return the normal first-year fraction of an addition.

        Half of the year for a class under the half-year rule, the whole
        year otherwise.
        """
        cca_class = asset.l10n_ca_cca_class_id
        if cca_class.half_year_rule and not asset.l10n_ca_cca_half_year_exempt:
            return context["half_year_factor"]
        return 1.0

    def _aiip_multiplier(self, asset):
        if asset.l10n_ca_cca_enhancement_excluded:
            return 1.0
        return asset.l10n_ca_cca_class_id._aiip_multiplier(
            self.company_id,
            asset.l10n_ca_cca_acquisition_date,
            asset.l10n_ca_cca_available_date,
            self.date_to,
            self.jurisdiction,
        )

    def _straight_line_annual(self, asset, cost):
        cca_class = asset.l10n_ca_cca_class_id
        life = asset.l10n_ca_cca_life_years
        min_years = cca_class._param(
            "min_years", self.date_to, self.company_id, self.jurisdiction
        )
        max_years = cca_class._param(
            "max_years", self.date_to, self.company_id, self.jurisdiction
        )
        if min_years is not None:
            life = max(life, min_years)
        if max_years is not None:
            life = min(life, max_years)
        if life <= 0:
            raise UserError(
                _(
                    "Set the CCA life of asset %(asset)s: class %(cca_class)s "
                    "is written off straight-line.",
                    asset=asset.display_name,
                    cca_class=cca_class.display_name,
                )
            )
        return cost / life

    def _add_addition(self, bucket, asset, cost, context):
        """Split a new addition between expensing, enhanced and regular.

        A per-asset first-year factor is capped so that the allowance of
        an asset never exceeds its own cost (a 100% class with a 3 times
        multiplier).
        """
        cca_class = asset.l10n_ca_cca_class_id
        acquired = asset.l10n_ca_cca_acquisition_date
        available = asset.l10n_ca_cca_available_date
        if cca_class.method == "straight_line":
            annual = self._straight_line_annual(asset, cost)
            if cca_class.half_year_rule:
                first = context["half_year_factor"]
            else:
                year_days = (self.date_to - self.date_from).days + 1
                first = ((self.date_to - available).days + 1) / year_days
            multiplier = self._aiip_multiplier(asset)
            bucket["straight_line_amount"] += min(cost, annual * first * multiplier)
            key = "additions_enhanced" if multiplier > 1.0 else "additions_regular"
            bucket[key] += cost
            return
        excluded = asset.l10n_ca_cca_enhancement_excluded
        if asset.l10n_ca_cca_immediate_expensing and not excluded:
            rate = cca_class._expensing_rate(
                self.company_id, acquired, available, self.date_to, self.jurisdiction
            )
            if rate:
                bucket["additions_expensing"] += cost
                bucket["expensing_allowance"] += cost * rate
                return
            if cca_class._diep_rate(
                self.company_id, acquired, available, self.date_to, self.jurisdiction
            ):
                if context["diep_left"] is None:
                    context["diep_left"] = (
                        self._param("diep.limit", default=0.0) * context["proration"]
                    )
                designated = min(cost, context["diep_left"])
                context["diep_left"] -= designated
                bucket["additions_expensing"] += designated
                bucket["expensing_allowance"] += designated
                cost -= designated
        if cost <= 0:
            return
        class_rate = cca_class._param(
            "rate", self.date_to, self.company_id, self.jurisdiction, default=0.0
        )
        factor = self._first_year_factor(asset, context)
        multiplier = self._aiip_multiplier(asset)
        base_factor = factor * multiplier
        if class_rate:
            base_factor = min(base_factor, 1.0 / class_rate)
        if multiplier > 1.0:
            bucket["additions_enhanced"] += cost
            bucket["enhanced_base"] += cost * base_factor
        else:
            bucket["additions_regular"] += cost
            bucket["regular_base"] += cost * base_factor

    def _bucket_vals(self, bucket, context, classes_with_assets):
        cca_class = bucket["class"]
        amounts = (
            bucket["opening_ucc"],
            bucket["adjustments"],
            bucket["additions_regular"],
            bucket["additions_enhanced"],
            bucket["additions_expensing"],
            bucket["dispositions"],
        )
        if not any(amounts) and not bucket["assets_remaining"]:
            return None
        if bucket["asset_id"] or cca_class in classes_with_assets:
            remaining = bucket["assets_remaining"]
        else:
            # A pool carried from before the asset register: its property is
            # presumed to remain until the user says otherwise.
            remaining = True
        normal = context["half_year_factor"] if cca_class.half_year_rule else 1.0
        rate = 0.0
        if cca_class.method != "straight_line":
            rate = cca_param(
                self.company_id,
                f"{cca_class.param_prefix}.rate",
                self.date_to,
                self.jurisdiction,
            )

        def ratio(base, amount, default):
            return base / amount if amount else default

        return {
            "schedule_id": self.id,
            "class_id": cca_class.id,
            "asset_id": bucket["asset_id"],
            "rate": rate,
            "half_year_factor": context["half_year_factor"],
            "proration": context["proration"],
            "opening_ucc": bucket["opening_ucc"],
            "adjustments": bucket["adjustments"],
            "additions_regular": bucket["additions_regular"],
            "regular_factor": ratio(
                bucket["regular_base"], bucket["additions_regular"], normal
            ),
            "additions_enhanced": bucket["additions_enhanced"],
            "enhanced_factor": ratio(
                bucket["enhanced_base"], bucket["additions_enhanced"], normal
            ),
            "additions_expensing": bucket["additions_expensing"],
            "expensing_rate": ratio(
                bucket["expensing_allowance"], bucket["additions_expensing"], 1.0
            ),
            "straight_line_amount": bucket["straight_line_amount"],
            "dispositions": bucket["dispositions"],
            "capital_gain": bucket["capital_gain"],
            "book_depreciation": bucket["book_depreciation"],
            "book_gain_loss": bucket["book_gain_loss"],
            "property_remaining": remaining,
        }


class L10nCaCcaScheduleLine(models.Model):
    """One class of a CCA schedule (a row of T2 Schedule 8).

    Inputs (opening balance, additions by kind, dispositions, factors) are
    stored and editable while the schedule is a draft; the maximum
    allowance, recapture, terminal loss and closing balance are computed
    from them.
    """

    _name = "l10n.ca.cca.schedule.line"
    _description = "Capital Cost Allowance Schedule Line"
    _order = "schedule_id, class_sequence, class_id, asset_id"

    schedule_id = fields.Many2one(
        "l10n.ca.cca.schedule", required=True, ondelete="cascade", index=True
    )
    state = fields.Selection(related="schedule_id.state")
    company_id = fields.Many2one(related="schedule_id.company_id", store=True)
    currency_id = fields.Many2one(related="schedule_id.currency_id")
    class_id = fields.Many2one(
        "l10n.ca.cca.class", string="Class", required=True, ondelete="restrict"
    )
    class_sequence = fields.Integer(related="class_id.sequence", store=True)
    method = fields.Selection(related="class_id.method")
    asset_id = fields.Many2one(
        "account.asset",
        string="Asset",
        help="Set when the asset is a separate class (class 10.1).",
    )
    rate = fields.Float(digits=(12, 4))
    half_year_factor = fields.Float(digits=(12, 4), default=0.5)
    proration = fields.Float(
        digits=(12, 6),
        default=1.0,
        help="Days of the taxation year / 365 for a short year (Reg. 1100(3)).",
    )
    opening_ucc = fields.Monetary(
        string="Opening UCC", help="Undepreciated capital cost at the start."
    )
    additions_regular = fields.Monetary(
        string="Additions (Regular)",
        help="Additions without enhancement, subject to the half-year rule "
        "when the class is.",
    )
    regular_factor = fields.Float(
        digits=(12, 4),
        default=0.5,
        help="Fraction of the net regular additions included in the CCA base.",
    )
    additions_enhanced = fields.Monetary(
        string="Additions (AIIP/RIIP)",
        help="Additions that are accelerated or reaccelerated investment "
        "incentive property.",
    )
    enhanced_factor = fields.Float(
        digits=(12, 4),
        default=1.5,
        help="Fraction of the net enhanced additions included in the CCA "
        "base (1.5 during the full incentive, 1.0 during the phase-out).",
    )
    additions_expensing = fields.Monetary(
        string="Additions (Immediate Expensing)",
    )
    expensing_rate = fields.Float(
        digits=(12, 4),
        default=1.0,
        help="Fraction of the net expensed additions deducted in the first year.",
    )
    additions = fields.Monetary(compute="_compute_amounts", store=True)
    adjustments = fields.Monetary(
        help="Manual change of the undepreciated capital cost: government "
        "assistance or tax credits received (negative), transfers, "
        "additional allowances not modelled.",
    )
    dispositions = fields.Monetary(
        help="Lesser of the proceeds of disposition and the capital cost of "
        "the property disposed of."
    )
    straight_line_amount = fields.Monetary(
        help="Straight-line classes: sum of the annual allowance of each "
        "asset, the first year reduced by the half-year rule or by days."
    )
    property_remaining = fields.Boolean(
        default=True,
        help="Some property of the class is still owned at the end of the "
        "year. When cleared, a positive balance is a terminal loss.",
    )
    ucc_before_cca = fields.Monetary(
        string="UCC before CCA", compute="_compute_amounts", store=True
    )
    cca_base = fields.Monetary(
        string="CCA Base",
        compute="_compute_amounts",
        store=True,
        help="Balance the rate applies to, after the half-year rule and the "
        "accelerated investment incentive adjustments.",
    )
    max_cca = fields.Monetary(
        string="Maximum CCA", compute="_compute_amounts", store=True
    )
    cca_claimed = fields.Monetary(
        string="CCA Claimed",
        help="Any amount from zero to the maximum. Claiming less keeps the "
        "balance for later years.",
    )
    recapture = fields.Monetary(compute="_compute_amounts", store=True)
    terminal_loss = fields.Monetary(compute="_compute_amounts", store=True)
    closing_ucc = fields.Monetary(
        string="Closing UCC", compute="_compute_amounts", store=True
    )
    book_depreciation = fields.Monetary(
        help="Depreciation posted in the books during the year for the "
        "assets of the class."
    )
    book_gain_loss = fields.Monetary(
        string="Book Gain/Loss",
        help="Proceeds minus net book value of the assets removed during the year.",
    )
    capital_gain = fields.Monetary(
        help="Proceeds in excess of the capital cost (T2 Schedule 6)."
    )
    book_tax_difference = fields.Monetary(
        string="Book - Tax",
        compute="_compute_amounts",
        store=True,
        help="Book depreciation minus CCA claimed.",
    )

    @api.depends(
        "opening_ucc",
        "adjustments",
        "additions_regular",
        "additions_enhanced",
        "additions_expensing",
        "regular_factor",
        "enhanced_factor",
        "expensing_rate",
        "dispositions",
        "straight_line_amount",
        "rate",
        "half_year_factor",
        "proration",
        "property_remaining",
        "cca_claimed",
        "book_depreciation",
        "class_id.method",
        "class_id.no_recapture_terminal_loss",
    )
    def _compute_amounts(self):
        for line in self:
            line.update(line._cca_amounts())

    def _cca_amounts(self):
        """Return the computed amounts of the line as a dict.

        Dispositions reduce the regular additions first, then the enhanced
        ones, then the expensed ones (T2 Schedule 8, columns 12 to 17).
        """
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        cca_class = self.class_id
        additions = (
            self.additions_regular + self.additions_enhanced + self.additions_expensing
        )
        ucc = self.opening_ucc + additions + self.adjustments - self.dispositions
        result = {
            "additions": additions,
            "ucc_before_cca": ucc,
            "cca_base": 0.0,
            "max_cca": 0.0,
            "recapture": 0.0,
            "terminal_loss": 0.0,
            "closing_ucc": 0.0,
            "book_tax_difference": self.book_depreciation - self.cca_claimed,
        }
        no_balance_effect = cca_class.no_recapture_terminal_loss
        if no_balance_effect and not self.property_remaining:
            # Reg. 1100(2.5): half the allowance on the opening balance in
            # the year of disposition; the balance then disappears.
            base = max(self.opening_ucc, 0.0) * self.half_year_factor
            result["cca_base"] = base
            result["max_cca"] = currency.round(base * self.rate * self.proration)
            return result
        if currency.compare_amounts(ucc, 0.0) < 0:
            if not no_balance_effect:
                result["recapture"] = -ucc
            return result
        if not self.property_remaining:
            if not no_balance_effect:
                result["terminal_loss"] = ucc
            return result
        left = self.dispositions
        nets = []
        for amount in (
            self.additions_regular,
            self.additions_enhanced,
            self.additions_expensing,
        ):
            used = min(max(amount, 0.0), max(left, 0.0))
            left -= used
            nets.append(amount - used)
        net_regular, net_enhanced, net_expensing = nets
        if self.method == "straight_line":
            base = ucc
            maximum = self.straight_line_amount * self.proration
        else:
            rest = ucc - net_regular - net_enhanced - net_expensing
            base = (
                rest
                + net_regular * self.regular_factor
                + net_enhanced * self.enhanced_factor
            )
            maximum = (
                self.rate * base + net_expensing * self.expensing_rate
            ) * self.proration
        result["cca_base"] = base
        result["max_cca"] = currency.round(min(max(maximum, 0.0), ucc))
        result["closing_ucc"] = ucc - self.cca_claimed
        return result

    @api.constrains("cca_claimed", "max_cca")
    def _check_cca_claimed(self):
        for line in self:
            currency = line.currency_id
            if currency.compare_amounts(line.cca_claimed, 0.0) < 0:
                raise ValidationError(_("The CCA claimed cannot be negative."))
            if currency.compare_amounts(line.cca_claimed, line.max_cca) > 0:
                raise ValidationError(
                    _(
                        "The CCA claimed for class %(cca_class)s (%(claimed)s) "
                        "exceeds the maximum of %(maximum)s.",
                        cca_class=line.class_id.display_name,
                        claimed=line.cca_claimed,
                        maximum=line.max_cca,
                    )
                )

    def _check_schedule_draft(self):
        if any(line.schedule_id.state == "locked" for line in self):
            raise UserError(_("The lines of a locked CCA schedule cannot change."))

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_schedule_draft()
        return lines

    def write(self, vals):
        self._check_schedule_draft()
        return super().write(vals)

    def unlink(self):
        self._check_schedule_draft()
        return super().unlink()
