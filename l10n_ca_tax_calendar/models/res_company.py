# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo import api, fields, models

QC_PAYROLL_FREQUENCIES = [
    ("none", "No payroll"),
    ("annual", "Annual"),
    ("quarterly", "Quarterly"),
    ("monthly", "Monthly"),
    ("twice_monthly", "Twice a month"),
    ("weekly", "Weekly"),
]

# Revenu Quebec frequency that matches each CRA remitter type, used when
# the company keeps the same frequency for both remittances.
FEDERAL_TO_QC_PAYROLL = {
    "none": "none",
    "quarterly": "quarterly",
    "regular": "monthly",
    "accelerated_1": "twice_monthly",
    "accelerated_2": "weekly",
}

# Holiday lines (by ``l10n_ca_jurisdiction``) that move the deadlines of
# each rule jurisdiction.
HOLIDAY_LINE_JURISDICTIONS = {
    "federal": ("both", "federal"),
    "quebec": ("both", "quebec"),
    "quebec_payroll": ("both", "quebec", "quebec_payroll"),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ca_gst_prior_net_tax = fields.Monetary(
        string="GST/HST Net Tax of the Previous Year",
        currency_field="currency_id",
        help="Net tax of the last fiscal year. An annual filer pays quarterly "
        "instalments when it reaches the threshold of the time parameter "
        "l10n_ca.tax_calendar.gst_instalment_threshold.",
    )
    l10n_ca_qst_prior_net_tax = fields.Monetary(
        string="QST Net Tax of the Previous Year",
        currency_field="currency_id",
        help="Net tax of the last fiscal year. An annual filer pays quarterly "
        "instalments when it reaches the threshold of the time parameter "
        "l10n_ca.tax_calendar.qst_instalment_threshold.",
    )
    l10n_ca_gst_instalments_required = fields.Boolean(
        string="GST/HST Instalments Required",
        compute="_compute_l10n_ca_instalments_required",
    )
    l10n_ca_qst_instalments_required = fields.Boolean(
        string="QST Instalments Required",
        compute="_compute_l10n_ca_instalments_required",
    )
    l10n_ca_files_t5 = fields.Boolean(
        string="Issues T5 and RL-3 Slips",
        help="The company pays dividends or interest reported on T5 and RL-3 slips.",
    )
    l10n_ca_req_combined_with_co17 = fields.Boolean(
        string="Annual Update Filed With the CO-17",
        default=True,
        help="The annual updating declaration of the enterprise register is "
        "combined with the Quebec income tax return. Otherwise it is filed "
        "during the yearly period set by the Registraire des entreprises.",
    )
    # Also declared, identically, by l10n_ca_corporate_tax: neither module
    # depends on the other, and each one reads the field.
    l10n_ca_qc_instalment_frequency = fields.Selection(
        [
            ("none", "None"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
        ],
        string="Quebec Income Tax Instalments",
        help="Frequency of the Quebec corporate income tax instalments, whose "
        "quarterly conditions differ from the federal ones. Empty: the "
        "federal frequency.",
    )
    l10n_ca_qc_payroll_frequency = fields.Selection(
        QC_PAYROLL_FREQUENCIES,
        string="Effective Revenu Quebec Remittance Frequency",
        compute="_compute_l10n_ca_qc_payroll_frequency",
    )
    l10n_ca_tax_deadline_user_id = fields.Many2one(
        "res.users",
        string="Tax Deadline Responsible",
        help="Receives the reminder activities of the tax deadlines whose "
        "rule names no responsible.",
    )
    l10n_ca_tax_deadline_reminder_days = fields.Integer(
        string="Tax Deadline Reminder (days)",
        default=14,
        help="A reminder activity is scheduled this many days before each due date.",
    )
    l10n_ca_tax_deadline_horizon_months = fields.Integer(
        string="Tax Deadline Horizon (months)",
        default=12,
        help="The scheduled action creates the deadlines due within this many months.",
    )

    @api.depends("l10n_ca_gst_prior_net_tax", "l10n_ca_qst_prior_net_tax")
    def _compute_l10n_ca_instalments_required(self):
        """Compare the net tax of the previous year with the dated threshold.

        A missing threshold parameter counts as a threshold of 0: any
        positive net tax then calls for instalments, which errs on the side
        of an extra reminder rather than a missed payment.
        """
        today = fields.Date.context_today(self)
        for company in self:
            gst_threshold = company._l10n_ca_param(
                "l10n_ca.tax_calendar.gst_instalment_threshold", today, default=0.0
            )
            qst_threshold = company._l10n_ca_param(
                "l10n_ca.tax_calendar.qst_instalment_threshold", today, default=0.0
            )
            company.l10n_ca_gst_instalments_required = (
                company.l10n_ca_gst_prior_net_tax > 0
                and company.l10n_ca_gst_prior_net_tax >= gst_threshold
            )
            company.l10n_ca_qst_instalments_required = (
                company.l10n_ca_qst_prior_net_tax > 0
                and company.l10n_ca_qst_prior_net_tax >= qst_threshold
            )

    @api.depends("l10n_ca_qc_remitter_type", "l10n_ca_payroll_remitter_type")
    def _compute_l10n_ca_qc_payroll_frequency(self):
        for company in self:
            frequency = company.l10n_ca_qc_remitter_type
            if not frequency:
                frequency = FEDERAL_TO_QC_PAYROLL.get(
                    company.l10n_ca_payroll_remitter_type or "none", "none"
                )
            company.l10n_ca_qc_payroll_frequency = frequency

    def _l10n_ca_holidays(self, jurisdiction, year):
        """Return the set of holiday dates of ``year`` for ``jurisdiction``.

        ``jurisdiction`` is a key of ``HOLIDAY_LINE_JURISDICTIONS``. A
        holiday line counts when its jurisdiction is one of the values of
        that key, its public holiday
        has the company country or no country, and its states, when it has
        any, include the province of the company. A company without province
        is taken as a Quebec company, the province this calendar serves.
        """
        self.ensure_one()
        country = self.country_id or self.env.ref("base.ca")
        province = self.state_id or self.env.ref(
            "base.state_ca_qc", raise_if_not_found=False
        )
        lines = (
            self.env["calendar.public.holiday.line"]
            .sudo()
            .search(
                [
                    ("date", ">=", date(year, 1, 1)),
                    ("date", "<=", date(year, 12, 31)),
                    ("public_holiday_id.country_id", "in", (False, country.id)),
                    (
                        "l10n_ca_jurisdiction",
                        "in",
                        HOLIDAY_LINE_JURISDICTIONS[jurisdiction],
                    ),
                ]
            )
        )
        return {
            line.date
            for line in lines
            if not line.state_ids or (province and province in line.state_ids)
        }
