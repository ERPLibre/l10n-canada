# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

from odoo.addons.l10n_ca_payroll.models.l10n_ca_payroll_t4 import T4_BOXES

# T4 boxes added for the employees working in Quebec: (field, CSV header).
QC_T4_BOXES = [
    ("box_55", "55 Employee's PPIP premiums"),
    ("box_56", "56 PPIP insurable earnings"),
]


class L10nCaPayrollT4Slip(models.Model):
    _inherit = "l10n_ca.payroll.t4.slip"

    box_55 = fields.Monetary(string="Box 55 - PPIP Premiums")
    box_56 = fields.Monetary(string="Box 56 - PPIP Insurable Earnings")


class L10nCaPayrollT4Summary(models.Model):
    _inherit = "l10n_ca.payroll.t4.summary"

    def _l10n_ca_t4_csv_rows(self):
        """Insert the PPIP boxes 55 and 56 in the slip rows of the export.

        The federal rows list the header, then one row per slip in the
        order of the employee names, then the summary rows, left as they
        are. The two columns go after the amount boxes, before the dental
        benefits code, so the trailing columns keep their position.
        """
        rows = super()._l10n_ca_t4_csv_rows()
        header = rows[0]
        position = 3 + len(T4_BOXES)
        rows[0] = (
            header[:position]
            + [label for _name, label in QC_T4_BOXES]
            + header[position:]
        )
        slips = self.slip_ids.sorted(lambda s: s.employee_id.name or "")
        for index, slip in enumerate(slips, start=1):
            row = rows[index]
            rows[index] = (
                row[:position]
                + [f"{slip[name]:.2f}" for name, _label in QC_T4_BOXES]
                + row[position:]
            )
        return rows
