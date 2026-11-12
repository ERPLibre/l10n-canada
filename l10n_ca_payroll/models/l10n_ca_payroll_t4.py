# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import calendar
import csv
import io
from collections import defaultdict
from datetime import date as Date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .l10n_ca_payroll_remittance import _next_weekday

# T4 slip boxes: (field, CSV header).
T4_BOXES = [
    ("box_14", "14 Employment income"),
    ("box_16", "16 Employee's CPP contributions"),
    ("box_16a", "16A Employee's second CPP contributions"),
    ("box_17", "17 Employee's QPP contributions"),
    ("box_17a", "17A Employee's second QPP contributions"),
    ("box_18", "18 Employee's EI premiums"),
    ("box_22", "22 Income tax deducted"),
    ("box_24", "24 EI insurable earnings"),
    ("box_26", "26 CPP/QPP pensionable earnings"),
    ("box_44", "44 Union dues"),
]

# T4 Summary lines: (field, CSV label).
SUMMARY_LINES = [
    ("line_14", "14 Employment income"),
    ("line_16", "16 Employees' CPP contributions"),
    ("line_16a", "16A Employees' second CPP contributions"),
    ("line_27", "27 Employer's CPP contributions"),
    ("line_27a", "27A Employer's second CPP contributions"),
    ("line_18", "18 Employees' EI premiums"),
    ("line_19", "19 Employer's EI premiums"),
    ("line_22", "22 Income tax deducted"),
    ("line_80", "80 Total deductions reported"),
    ("line_82", "82 Minus: remittances"),
    ("line_84", "84 Overpayment"),
    ("line_86", "86 Balance due"),
    ("line_88", "88 Total number of T4 slips filed"),
]


def _csv_file(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return base64.b64encode(buffer.getvalue().encode("utf-8"))


def _amount(value):
    return f"{value:.2f}"


class L10nCaPayrollT4Summary(models.Model):
    _name = "l10n_ca.payroll.t4.summary"
    _description = "Canadian Payroll Year-End (T4 Summary)"
    _order = "year desc, company_id"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    year = fields.Integer(
        required=True,
        default=lambda self: fields.Date.context_today(self).year - 1,
    )
    due_date = fields.Date(
        compute="_compute_due_date",
        store=True,
        help="Filing deadline: last day of the month set by the time "
        "parameter l10n_ca.t4.due_month, in the year after the slips, moved "
        "to the next Monday when it falls on a weekend.",
    )
    slip_ids = fields.One2many(
        "l10n_ca.payroll.t4.slip", "summary_id", string="T4 Slips"
    )
    remittance_ids = fields.One2many(
        "l10n_ca.payroll.remittance", "summary_id", string="Remittances"
    )
    line_14 = fields.Monetary(compute="_compute_lines", store=True)
    line_16 = fields.Monetary(compute="_compute_lines", store=True)
    line_16a = fields.Monetary(compute="_compute_lines", store=True)
    line_18 = fields.Monetary(compute="_compute_lines", store=True)
    line_19 = fields.Monetary(compute="_compute_lines", store=True)
    line_22 = fields.Monetary(compute="_compute_lines", store=True)
    line_27 = fields.Monetary(compute="_compute_lines", store=True)
    line_27a = fields.Monetary(compute="_compute_lines", store=True)
    line_80 = fields.Monetary(compute="_compute_lines", store=True)
    line_82 = fields.Monetary(
        compute="_compute_lines",
        store=True,
        help="Amounts paid on the remittances of the year.",
    )
    line_84 = fields.Monetary(compute="_compute_lines", store=True)
    line_86 = fields.Monetary(compute="_compute_lines", store=True)
    line_88 = fields.Integer(compute="_compute_lines", store=True)
    csv_file = fields.Binary(string="CSV File", attachment=False, readonly=True)
    csv_filename = fields.Char()

    _sql_constraints = [
        (
            "company_year_unique",
            "unique (company_id, year)",
            "A company has one year-end summary per year.",
        ),
    ]

    @api.depends("year")
    def _compute_name(self):
        for summary in self:
            summary.name = _("T4 Summary %(year)s", year=summary.year)

    @api.depends("year", "company_id")
    def _compute_due_date(self):
        for summary in self:
            if not summary.year:
                summary.due_date = False
                continue
            following = summary.year + 1
            month = summary.company_id._l10n_ca_param(
                "l10n_ca.t4.due_month", Date(following, 1, 1), default=2
            )
            last_day = calendar.monthrange(following, int(month))[1]
            summary.due_date = _next_weekday(Date(following, int(month), last_day))

    @api.depends(
        "slip_ids.box_14",
        "slip_ids.box_16",
        "slip_ids.box_16a",
        "slip_ids.box_18",
        "slip_ids.box_22",
        "slip_ids.employer_cpp",
        "slip_ids.employer_cpp2",
        "slip_ids.employer_ei",
        "remittance_ids.amount_paid",
    )
    def _compute_lines(self):
        for summary in self:
            slips = summary.slip_ids
            vals = {
                "line_14": sum(slips.mapped("box_14")),
                "line_16": sum(slips.mapped("box_16")),
                "line_16a": sum(slips.mapped("box_16a")),
                "line_18": sum(slips.mapped("box_18")),
                "line_19": sum(slips.mapped("employer_ei")),
                "line_22": sum(slips.mapped("box_22")),
                "line_27": sum(slips.mapped("employer_cpp")),
                "line_27a": sum(slips.mapped("employer_cpp2")),
                "line_82": sum(summary.remittance_ids.mapped("amount_paid")),
                "line_88": len(slips),
            }
            vals["line_80"] = sum(
                vals[key]
                for key in (
                    "line_16",
                    "line_16a",
                    "line_18",
                    "line_19",
                    "line_22",
                    "line_27",
                    "line_27a",
                )
            )
            difference = summary.currency_id.round(vals["line_80"] - vals["line_82"])
            vals["line_84"] = -difference if difference < 0 else 0.0
            vals["line_86"] = difference if difference > 0 else 0.0
            summary.update(vals)

    def _l10n_ca_year_payslips(self):
        self.ensure_one()
        return self.env["hr.payslip"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "done"),
                ("l10n_ca_pay_date", ">=", Date(self.year, 1, 1)),
                ("l10n_ca_pay_date", "<=", Date(self.year, 12, 31)),
            ]
        )

    def action_compute_slips(self):
        """Rebuild the T4 slips from the done payslips of the year.

        One slip per employee and province of employment, as the CRA
        requires a separate slip for each province.
        """
        Slip = self.env["l10n_ca.payroll.t4.slip"]
        for summary in self:
            summary.slip_ids.unlink()
            groups = defaultdict(lambda: self.env["hr.payslip"])
            for payslip in summary._l10n_ca_year_payslips():
                groups[(payslip.employee_id, payslip.l10n_ca_province_id)] |= payslip
            vals_list = []
            for (employee, _province), payslips in groups.items():
                vals = {
                    "summary_id": summary.id,
                    "employee_id": employee.id,
                    "payslip_ids": [(6, 0, payslips.ids)],
                }
                vals.update(payslips._l10n_ca_t4_values(summary.year))
                vals_list.append(vals)
            Slip.create(vals_list)
        return True

    def action_compute_remittances(self):
        Remittance = self.env["l10n_ca.payroll.remittance"]
        for summary in self:
            Remittance._l10n_ca_generate(summary.company_id, summary.year, summary)
        return True

    def _l10n_ca_t4_csv_rows(self):
        """Rows of the T4 export: one row per slip, then the summary lines.

        Columns follow the boxes of the T4 Web Forms, amounts with two
        decimals and no thousands separator.
        """
        self.ensure_one()
        header = [
            "Employee",
            "SIN (12)",
            "Province of employment (10)",
            *[label for _field, label in T4_BOXES],
            "Dental benefits code (45)",
            "CPP/QPP exempt (28)",
            "EI exempt (28)",
        ]
        rows = [header]
        for slip in self.slip_ids.sorted(lambda s: s.employee_id.name or ""):
            rows.append(
                [
                    slip.employee_id.name,
                    slip.sin or "",
                    slip.province_code or "",
                    *[_amount(slip[name]) for name, _label in T4_BOXES],
                    slip.box_45 or "",
                    "X" if slip.cpp_exempt else "",
                    "X" if slip.ei_exempt else "",
                ]
            )
        rows.append([])
        rows.append(
            [
                "T4 Summary",
                str(self.year),
                self.company_id.l10n_ca_payroll_account_number or "",
            ]
        )
        for name, label in SUMMARY_LINES:
            value = self[name]
            rows.append([label, value if name == "line_88" else _amount(value)])
        return rows

    def _l10n_ca_pd7a_csv_rows(self):
        self.ensure_one()
        fields_order = [
            ("date_from", "Paid from"),
            ("date_to", "Paid to"),
            ("due_date", "Due date"),
            ("employee_count", "Employees in last pay period"),
            ("gross_payroll", "Gross payroll"),
            ("cpp_employee", "CPP employee"),
            ("cpp_employer", "CPP employer"),
            ("cpp2_employee", "CPP2 employee"),
            ("cpp2_employer", "CPP2 employer"),
            ("ei_employee", "EI employee"),
            ("ei_employer", "EI employer"),
            ("income_tax", "Income tax"),
            ("total", "Current source deductions"),
            ("amount_paid", "Amount paid"),
            ("payment_date", "Payment date"),
        ]
        rows = [[label for _name, label in fields_order]]
        for remittance in self.remittance_ids.sorted("date_from"):
            row = []
            for name, _label in fields_order:
                value = remittance[name]
                if isinstance(value, float):
                    value = _amount(value)
                row.append(value or "")
            rows.append(row)
        return rows

    def _l10n_ca_download(self, rows, filename):
        self.ensure_one()
        self.write({"csv_file": _csv_file(rows), "csv_filename": filename})
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self._name}/{self.id}/csv_file/{filename}"
            "?download=true",
            "target": "self",
        }

    def action_export_t4_csv(self):
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(_("Compute the T4 slips before exporting them."))
        return self._l10n_ca_download(
            self._l10n_ca_t4_csv_rows(), f"T4_{self.year}.csv"
        )

    def action_export_pd7a_csv(self):
        self.ensure_one()
        if not self.remittance_ids:
            raise UserError(_("Compute the remittances before exporting them."))
        return self._l10n_ca_download(
            self._l10n_ca_pd7a_csv_rows(), f"PD7A_{self.year}.csv"
        )


class L10nCaPayrollT4Slip(models.Model):
    _name = "l10n_ca.payroll.t4.slip"
    _description = "T4 Slip"
    _order = "summary_id, employee_id"

    summary_id = fields.Many2one(
        "l10n_ca.payroll.t4.summary",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="summary_id.company_id", store=True)
    currency_id = fields.Many2one(related="summary_id.currency_id")
    year = fields.Integer(related="summary_id.year", store=True)
    employee_id = fields.Many2one("hr.employee", required=True)
    sin = fields.Char(
        string="SIN",
        compute="_compute_sin",
        compute_sudo=True,
        help="Social insurance number, from the identification number of the employee.",
    )
    province_code = fields.Char(string="Province of Employment (Box 10)")
    payslip_ids = fields.Many2many("hr.payslip", string="Payslips")
    box_14 = fields.Monetary(string="Box 14 - Employment Income")
    box_16 = fields.Monetary(string="Box 16 - CPP Contributions")
    box_16a = fields.Monetary(string="Box 16A - Second CPP Contributions")
    box_17 = fields.Monetary(string="Box 17 - QPP Contributions")
    box_17a = fields.Monetary(string="Box 17A - Second QPP Contributions")
    box_18 = fields.Monetary(string="Box 18 - EI Premiums")
    box_22 = fields.Monetary(string="Box 22 - Income Tax Deducted")
    box_24 = fields.Monetary(string="Box 24 - EI Insurable Earnings")
    box_26 = fields.Monetary(string="Box 26 - CPP/QPP Pensionable Earnings")
    box_44 = fields.Monetary(string="Box 44 - Union Dues")
    box_45 = fields.Selection(
        selection=lambda self: (
            self.env["hr.contract"]
            ._fields["l10n_ca_t4_dental_code"]
            ._description_selection(self.env)
        ),
        string="Box 45 - Employer-Offered Dental Benefits",
    )
    cpp_exempt = fields.Boolean(string="Box 28 - CPP/QPP Exempt")
    ei_exempt = fields.Boolean(string="Box 28 - EI Exempt")
    employer_cpp = fields.Monetary(string="Employer CPP")
    employer_cpp2 = fields.Monetary(string="Employer CPP2")
    employer_ei = fields.Monetary(string="Employer EI")

    @api.depends("employee_id")
    def _compute_sin(self):
        for slip in self:
            slip.sin = slip.employee_id.ssnid
