# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CalendarPublicHolidayLine(models.Model):
    _inherit = "calendar.public.holiday.line"

    l10n_ca_jurisdiction = fields.Selection(
        [
            ("both", "Federal and Quebec"),
            ("federal", "Federal only"),
            ("quebec", "Quebec only"),
            ("quebec_payroll", "Revenu Quebec closed (source deductions)"),
        ],
        string="Canadian Deadlines Moved",
        default="both",
        required=True,
        help="Deadlines that move to the next business day when they fall on "
        "this holiday: federal ones (CRA), Quebec ones (Revenu Quebec, "
        "Registraire des entreprises, CNESST) or both. A day Revenu Quebec "
        "is closed without being a legal holiday moves only the source "
        "deduction remittances to Revenu Quebec.",
    )
