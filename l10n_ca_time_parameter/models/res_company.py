# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError

FILING_FREQUENCIES = [
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("annual", "Annual"),
]

_NO_DEFAULT = object()


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_neq = fields.Char(
        string="Quebec Enterprise Number (NEQ)",
        size=10,
    )
    l10n_ca_ccpc = fields.Boolean(
        string="Canadian-Controlled Private Corporation",
        default=True,
        help="Enables the small business deduction and the CCPC rules "
        "(quarterly instalments, enhanced refundable credits).",
    )
    l10n_ca_gst_filing_frequency = fields.Selection(
        FILING_FREQUENCIES,
        string="GST/HST Filing Frequency",
        default="annual",
    )
    l10n_ca_qst_filing_frequency = fields.Selection(
        FILING_FREQUENCIES,
        string="QST Filing Frequency",
        default="annual",
    )
    l10n_ca_quick_method = fields.Boolean(
        string="Quick Method of Accounting",
        help="The GST/HST and QST returns use the quick method: tax remitted is a "
        "fixed percentage of tax-included sales. It is not available to "
        "businesses that provide legal, accounting or actuarial services, "
        "bookkeeping, financial or tax consulting, or that prepare tax "
        "returns, nor to listed financial institutions, charities, qualifying "
        "non-profit organizations and selected public service bodies.",
    )
    l10n_ca_quick_method_date = fields.Date(
        string="Quick Method Effective Date",
    )
    l10n_ca_quick_method_activity = fields.Selection(
        [
            ("service", "Services"),
            ("resale", "Purchase for resale"),
        ],
        string="Quick Method Activity",
        default="service",
        help="Selects the remittance rate table: service businesses and resellers "
        "have different quick method rates. The resale rates require that the "
        "cost of the goods purchased for resale, basic groceries excluded, is "
        "at least 40% of the annual taxable sales.",
    )
    l10n_ca_instalment_frequency = fields.Selection(
        [
            ("none", "None"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
        ],
        string="Income Tax Instalments",
        default="none",
    )
    l10n_ca_payroll_remitter_type = fields.Selection(
        [
            ("none", "No payroll"),
            ("quarterly", "Quarterly"),
            ("regular", "Regular (monthly)"),
            ("accelerated_1", "Accelerated threshold 1 (twice a month)"),
            ("accelerated_2", "Accelerated threshold 2 (up to 4 times a month)"),
        ],
        string="Source Deduction Remitter Type",
        default="none",
    )
    l10n_ca_qc_remitter_type = fields.Selection(
        [
            ("annual", "Annual"),
            ("quarterly", "Quarterly"),
            ("monthly", "Monthly"),
            ("twice_monthly", "Twice a month"),
            ("weekly", "Weekly"),
        ],
        string="Revenu Quebec Remittance Frequency",
        help="Frequency assigned by Revenu Quebec to the remittances of "
        "source deductions and employer contributions, with its own "
        "thresholds. Empty: the frequency that matches the CRA remitter type.",
    )

    def _l10n_ca_param_version(self, code, date=None):
        """Return the ``base.time.parameter.version`` in force at ``date``.

        A parameter of this company wins over a parameter without company.
        Reads as superuser: the parameters are reference data that payroll
        and accounting users need without holding the time parameter group,
        and the multi-company rule of ``base_time_parameter`` hides records
        without company. Returns an empty recordset when nothing applies.
        """
        self.ensure_one()
        if isinstance(date, datetime.datetime):
            date = date.date()
        date = date or fields.Date.context_today(self)
        parameters = (
            self.env["base.time.parameter"]
            .sudo()
            .search(
                [("code", "=", code), ("company_id", "in", (self.id, False))],
                order="company_id",
            )
        )
        # order="company_id" puts NULL last in PostgreSQL ascending order.
        for parameter in parameters:
            versions = parameter.version_ids.filtered(
                lambda v, d=date: v.date_from <= d
            ).sorted("date_from", reverse=True)
            if versions:
                return versions[0]
        return self.env["base.time.parameter.version"]

    def _l10n_ca_param(self, code, date=None, default=_NO_DEFAULT):
        """Return the typed value of parameter ``code`` at ``date``.

        Unlike ``get_time_parameter``, a value of 0 or False is returned as
        is instead of being taken for a missing parameter. Without
        ``default``, a missing parameter raises a UserError that names the
        code and the date, so a gap in the tables stops the computation
        instead of producing a silent zero.
        """
        version = self._l10n_ca_param_version(code, date)
        if not version:
            if default is not _NO_DEFAULT:
                return default
            raise UserError(
                _(
                    "No Canadian time parameter '%(code)s' in force on "
                    "%(date)s. Add a version under Invoicing (Accounting) > "
                    "Configuration > Canadian Time Parameters.",
                    code=code,
                    date=date or fields.Date.context_today(self),
                )
            )
        return version.parameter_id.sudo()._get(version.date_from)
