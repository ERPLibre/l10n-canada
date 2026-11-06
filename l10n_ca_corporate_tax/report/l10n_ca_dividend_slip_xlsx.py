# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, models

from ..models.l10n_ca_dividend_slip import BOX_FIELDS


class L10nCaDividendSlipXlsx(models.AbstractModel):
    _name = "report.l10n_ca_corporate_tax.dividend_slip_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "T5 and RL-3 Dividend Slips Workbook"

    def generate_xlsx_report(self, workbook, data, slips):
        """Write one row per slip, the boxes in columns, then the totals."""
        sheet = workbook.add_worksheet(_("Dividend slips"))
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        header = [_("Year"), _("Recipient"), _("T5 Required")] + [
            self.env._(label) for _n, label in BOX_FIELDS
        ]
        for column, title in enumerate(header):
            sheet.write(0, column, title, bold)
        row = 0
        for row, slip in enumerate(slips, start=1):
            sheet.write(row, 0, slip.year)
            sheet.write(row, 1, slip.partner_id.name or "")
            sheet.write(row, 2, _("Yes") if slip.t5_required else _("No"))
            for column, (name, _label) in enumerate(BOX_FIELDS, start=3):
                sheet.write_number(row, column, slip[name], money)
        summary = slips._l10n_ca_summary()
        total_row = row + 1
        sheet.write(total_row, 1, _("Total"), bold)
        sheet.write(total_row, 2, summary["t5_count"], bold)
        for column, (name, _label) in enumerate(BOX_FIELDS, start=3):
            sheet.write_number(total_row, column, summary[name], money)
        sheet.set_column(1, 1, 30)
        sheet.set_column(3, 2 + len(BOX_FIELDS), 18)
