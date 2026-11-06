# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class L10nCaGifiStatementXlsx(models.AbstractModel):
    """Workbook of a GIFI statement: one sheet per schedule, one for the
    checks. Amounts are written as numbers, in whole dollars."""

    _name = "report.l10n_ca_gifi.statement_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "GIFI Statement XLSX"

    def generate_xlsx_report(self, workbook, data, objects):
        bold = workbook.add_format({"bold": True})
        amount = workbook.add_format({"num_format": "#,##0;-#,##0"})
        amount_bold = workbook.add_format({"num_format": "#,##0;-#,##0", "bold": True})
        # Labels in the language of the user who prints the workbook.
        schedules = dict(
            self.env["l10n.ca.gifi.statement.line"]
            ._fields["schedule"]
            ._description_selection(self.env)
        )
        levels = dict(
            self.env["l10n.ca.gifi.statement.check"]
            ._fields["level"]
            ._description_selection(self.env)
        )
        for index, statement in enumerate(objects, start=1):
            # Sheet names are unique in a workbook: several statements of
            # the same year (several companies) are told apart by position.
            suffix = f" {index}" if len(objects) > 1 else ""
            for schedule, title in schedules.items():
                lines = statement._lines_of(schedule)
                if not lines:
                    continue
                sheet = workbook.add_worksheet(f"S{schedule}{suffix}"[:31])
                sheet.set_column(0, 0, 8)
                sheet.set_column(1, 1, 70)
                sheet.set_column(2, 2, 16)
                sheet.write(0, 0, f"{statement.company_id.name} - {title}", bold)
                sheet.write(
                    1,
                    0,
                    f"{statement.date_from.isoformat()} - "
                    f"{statement.date_to.isoformat()}",
                )
                headers = [self.env._("Code"), self.env._("Item"), self.env._("Amount")]
                sheet.write_row(3, 0, headers, bold)
                for row, line in enumerate(lines, start=4):
                    style = amount_bold if line.is_total else amount
                    sheet.write(row, 0, line.code, bold if line.is_total else None)
                    sheet.write(row, 1, line.name)
                    sheet.write_number(row, 2, line.amount, style)
            sheet = workbook.add_worksheet(f"{self.env._('Checks')}{suffix}"[:31])
            sheet.set_column(0, 0, 14)
            sheet.set_column(1, 1, 110)
            sheet.write_row(0, 0, [self.env._("Level"), self.env._("Message")], bold)
            for row, check in enumerate(statement.check_ids, start=1):
                sheet.write(row, 0, levels[check.level])
                sheet.write(row, 1, check.message)
