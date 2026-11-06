# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, models


class TaxReturnXlsx(models.AbstractModel):
    _name = "report.l10n_ca_tax_return.tax_return_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Canadian Sales Tax Return XLSX"

    def generate_xlsx_report(self, workbook, data, returns):
        """Write one sheet per return: header, then one row per form line.

        Columns: line number, description, amount. Totals are in bold, and
        amounts computed by the quick method are flagged in a fourth column.
        Labels are in the language of the reader, like the line names.
        """
        bold = workbook.add_format({"bold": True})
        title = workbook.add_format({"bold": True, "font_size": 14})
        for tax_return in returns:
            money = workbook.add_format(
                {
                    "num_format": self._report_xlsx_currency_format(
                        tax_return.currency_id
                    )
                }
            )
            money_bold = workbook.add_format(
                {
                    "bold": True,
                    "num_format": self._report_xlsx_currency_format(
                        tax_return.currency_id
                    ),
                }
            )
            # Sheet names are unique in a workbook and hold 31 characters:
            # the id tells apart two returns of the same kind and period.
            sheet = workbook.add_worksheet(
                f"{tax_return.id} {tax_return.kind} {tax_return.date_to}"[:31]
            )
            sheet.set_column(0, 0, 8)
            sheet.set_column(1, 1, 70)
            sheet.set_column(2, 2, 16)
            sheet.set_column(3, 3, 14)
            sheet.write(0, 0, tax_return.name, title)
            selection = {
                name: dict(tax_return._fields[name]._description_selection(self.env))
                for name in ("method", "state")
            }
            header = [
                (_("Company"), tax_return.company_id.name),
                (
                    _("Quebec enterprise number"),
                    tax_return.company_id.l10n_ca_neq or "",
                ),
                (_("Business number"), tax_return.company_id.vat or ""),
                (_("Period"), f"{tax_return.date_from} - {tax_return.date_to}"),
                (_("Method"), selection["method"][tax_return.method]),
                (_("Due Date"), str(tax_return.date_due or "")),
                (_("Status"), selection["state"][tax_return.state]),
            ]
            if tax_return.filing_date:
                header.append((_("Filing Date"), str(tax_return.filing_date)))
            if tax_return.confirmation_number:
                header.append(
                    (_("Confirmation Number"), tax_return.confirmation_number)
                )
            row = 2
            for label, value in header:
                sheet.write(row, 0, label, bold)
                sheet.write(row, 2, value)
                row += 1
            row += 1
            for col, label in enumerate(
                (_("Line"), _("Description"), _("Amount"), _("Quick method"))
            ):
                sheet.write(row, col, label, bold)
            for line in tax_return.line_ids:
                row += 1
                total = line.hierarchy_level <= 1
                sheet.write(row, 0, line.code, bold if total else None)
                sheet.write(row, 1, line.name, bold if total else None)
                sheet.write_number(row, 2, line.amount, money_bold if total else money)
                sheet.write(row, 3, "x" if line.is_quick_method else "")
            row += 2
            sheet.write(row, 1, _("Net Tax"), bold)
            sheet.write_number(row, 2, tax_return.net_tax, money_bold)
            if tax_return.method == "quick":
                row += 1
                sheet.write(row, 1, _("Quick Method Gain"), bold)
                sheet.write_number(row, 2, tax_return.quick_method_gain, money_bold)
