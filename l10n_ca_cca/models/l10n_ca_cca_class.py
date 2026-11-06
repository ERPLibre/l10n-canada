# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models

from ..tools import cca_param, window_value


class L10nCaCcaClass(models.Model):
    """A class of depreciable property of Schedule II of the regulations.

    The class holds the rules that do not move with budgets (method,
    half-year rule, eligibility to the incentives). Rates, limits and
    enhancement windows are dated parameters named
    ``l10n_ca.cca.class_<number>.<key>``, the number written with ``_``
    instead of ``.`` (``class_10_1.rate``).
    """

    _name = "l10n.ca.cca.class"
    _description = "Capital Cost Allowance Class"
    _order = "sequence, id"
    _rec_names_search = ["number", "name"]

    number = fields.Char(required=True, help="Class number, e.g. 8 or 10.1.")
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    method = fields.Selection(
        [
            ("declining", "Declining balance"),
            ("straight_line", "Straight-line over the life"),
            ("full", "Full write-off (100% class)"),
        ],
        required=True,
        default="declining",
        help="Declining balance applies the rate parameter to the "
        "undepreciated capital cost. Straight-line (classes 13 and 14) "
        "spreads the capital cost of each asset over its life. Full "
        "write-off is the declining balance at a 100% rate (class 12).",
    )
    half_year_rule = fields.Boolean(
        default=True,
        help="Only half of the net additions of the year enter the CCA base "
        "(Reg. 1100(2)), unless the property is an accelerated investment "
        "incentive property or is expensed.",
    )
    aiip_eligible = fields.Boolean(
        string="Accelerated Investment Incentive",
        default=True,
        help="New additions of this class get the enhanced first-year "
        "allowance of the accelerated or reaccelerated investment incentive "
        "when their dates fall in a window of parameter "
        "l10n_ca.cca.class_<number>.aiip.windows, or of "
        "l10n_ca.cca.aiip.windows when the class has none.",
    )
    immediate_expensing_eligible = fields.Boolean(
        string="CCPC Immediate Expensing",
        default=True,
        help="The class may hold designated immediate expensing property of "
        "a CCPC (parameter l10n_ca.cca.diep.windows). Classes 1 to 6, 14.1, "
        "17, 47, 49 and 51 are excluded by the regulations.",
    )
    separate_class = fields.Boolean(
        string="Separate Class per Property",
        help="Each asset is its own class on the schedule (class 10.1).",
    )
    no_recapture_terminal_loss = fields.Boolean(
        string="No Recapture or Terminal Loss",
        help="On disposition, the balance is dropped without recapture or "
        "terminal loss, and half of the allowance on the opening balance "
        "is allowed in the year of disposition (class 10.1, ITA 20(16.1), "
        "Reg. 1100(2.5)).",
    )
    param_prefix = fields.Char(
        compute="_compute_param_prefix",
        help="Parameter code prefix of the class, after 'l10n_ca.cca.'.",
    )
    current_rate = fields.Float(
        compute="_compute_current_rate",
        digits=(12, 4),
        help="Rate in force today, read from the class rate parameter.",
    )
    note = fields.Text(help="Content of the class and particular rules.")
    quebec_note = fields.Text(
        string="Quebec Differences",
        help="Where the Quebec Taxation Act departs from the federal rules "
        "for this class. A Quebec schedule reads a parameter "
        "l10n_ca.cca.qc.<key> first, then the federal one.",
    )

    _sql_constraints = [
        ("number_unique", "unique(number)", "A CCA class number must be unique."),
    ]

    @api.depends("number")
    def _compute_param_prefix(self):
        for cca_class in self:
            cca_class.param_prefix = "class_" + (cca_class.number or "").replace(
                ".", "_"
            )

    def _compute_current_rate(self):
        company = self.env.company
        for cca_class in self:
            cca_class.current_rate = (
                cca_class._param("rate", fields.Date.context_today(self), company)
                or 0.0
            )

    @api.depends("number", "name")
    def _compute_display_name(self):
        for cca_class in self:
            cca_class.display_name = f"{cca_class.number} - {cca_class.name}"

    def _param(self, key, date, company, jurisdiction="federal", default=None):
        """Return parameter ``class_<number>.<key>`` or ``default``."""
        self.ensure_one()
        return cca_param(
            company,
            f"{self.param_prefix}.{key}",
            date,
            jurisdiction=jurisdiction,
            default=default,
        )

    def _expensing_rate(self, company, acquired, available, date, jurisdiction):
        """Return the immediate expensing rate of a new addition of the class.

        Reads the class windows ``class_<number>.expensing`` in force at
        ``date``. Returns 0.0 when no window applies.
        """
        self.ensure_one()
        windows = self._param("expensing", date, company, jurisdiction, default=[])
        return window_value(windows, acquired, available, "rate")

    def _diep_rate(self, company, acquired, available, date, jurisdiction):
        """Return 1.0 when the addition can be a CCPC designated property."""
        self.ensure_one()
        if not (company.l10n_ca_ccpc and self.immediate_expensing_eligible):
            return 0.0
        windows = cca_param(
            company, "diep.windows", date, jurisdiction=jurisdiction, default=[]
        )
        return window_value(windows, acquired, available, "rate")

    def _aiip_multiplier(self, company, acquired, available, date, jurisdiction):
        """Return the multiplier of the normal first-year allowance.

        1.0 when the property is not accelerated investment incentive
        property. The multiplier is relative to the normal first-year
        allowance: 3 on a half-year rule class gives 1.5 times the rate.
        The class windows ``class_<number>.aiip.windows`` replace the
        general ``aiip.windows`` when they are in force at ``date``.
        """
        self.ensure_one()
        if not self.aiip_eligible:
            return 1.0
        windows = self._param("aiip.windows", date, company, jurisdiction)
        if windows is None:
            windows = cca_param(
                company, "aiip.windows", date, jurisdiction=jurisdiction, default=[]
            )
        key = "hyr" if self.half_year_rule else "no_hyr"
        return window_value(windows, acquired, available, key) or 1.0
