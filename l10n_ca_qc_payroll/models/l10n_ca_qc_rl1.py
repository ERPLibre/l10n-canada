# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import calendar
from collections import defaultdict
from datetime import date as Date
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import LazyTranslate

from odoo.addons.l10n_ca_payroll.models.l10n_ca_payroll_t4 import _amount, _csv_file

_lt = LazyTranslate(__name__)

# RL-1 slip boxes: (field, CSV header). The headers are lazy terms, written
# in the language of the user who exports.
RL1_BOXES = [
    ("box_a", _lt("A Employment income")),
    ("box_b_a", _lt("B.A QPP contribution")),
    ("box_b_b", _lt("B.B Additional QPP contribution")),
    ("box_c", _lt("C EI premium")),
    ("box_e", _lt("E Quebec income tax withheld")),
    ("box_f", _lt("F Union dues")),
    ("box_g", _lt("G Pensionable salary or wages under the QPP")),
    ("box_h", _lt("H QPIP premium")),
    ("box_i", _lt("I Eligible salary or wages under the QPIP")),
]

# RL-1 summary (RLZ-1.S) lines: (field, CSV label), lazy terms as above.
SUMMARY_LINES = [
    ("line_21", _lt("21 QPP - employee contributions")),
    ("line_22", _lt("22 QPP - employer contribution")),
    ("line_23", _lt("23 QPP - employee additional contributions")),
    ("line_24", _lt("24 QPP - employer additional contribution")),
    ("line_25", _lt("25 QPP - total")),
    ("line_28", _lt("28 QPIP - employee premiums")),
    ("line_29", _lt("29 QPIP - employer premium")),
    ("line_30", _lt("30 QPIP - total")),
    ("line_35", _lt("35 Quebec income tax withheld (RL-1)")),
    ("line_38", _lt("38 Total source deductions")),
    ("line_44", _lt("44 QPP paid or payable in the year")),
    ("line_45", _lt("45 QPIP paid or payable in the year")),
    ("line_46", _lt("46 Income tax paid or payable in the year")),
    ("line_47", _lt("47 Total paid or payable")),
    ("line_48", _lt("48 Balance (refund if negative)")),
    ("line_50_1", _lt("50.1 Total payroll")),
    ("line_51", _lt("51 Salaries subject to the HSF")),
    ("line_52_1", _lt("52.1 HSF contribution credit specification")),
    ("line_52", _lt("52 Salaries eligible for an HSF contribution credit")),
    ("line_53", _lt("53 Line 51 minus line 52")),
    ("line_54", _lt("54 HSF contribution rate (%)")),
    ("line_55", _lt("55 HSF contribution")),
    ("line_56", _lt("56 HSF paid or payable in the year")),
    ("line_57", _lt("57 HSF balance")),
    ("line_61", _lt("61 Remuneration subject to the labour standards contribution")),
    ("line_63", _lt("63 Labour standards contribution")),
    ("line_64", _lt("64 Labour standards contribution paid")),
    ("line_71", _lt("71 Total payroll (WSDRF)")),
    ("line_73", _lt("73 Participation (line 71 x 1%)")),
    ("line_74", _lt("74 Eligible training expenditures used")),
    ("line_75", _lt("75 WSDRF contribution")),
    ("line_80", _lt("80 Balance")),
    ("line_81", _lt("81 Refund")),
    ("line_82", _lt("82 Balance due")),
]

# Summary lines entered by the user, exported with the computed ones.
_ENTERED_LINES = ("line_52_1", "line_52")

# Every field computed by _compute_lines.
_COMPUTED_LINES = [
    name for name, _label in SUMMARY_LINES if name not in _ENTERED_LINES
] + [
    "hsf_accrued",
    "cnesst_insurable",
    "cnesst_paid",
]


class L10nCaQcRl1Summary(models.Model):
    _name = "l10n_ca.qc.rl1.summary"
    _description = "Quebec Payroll Year-End (RL-1 Summary)"
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
        help="Filing deadline of the RL-1 slips and summary, and payment "
        "deadline of the labour standards and WSDRF contributions: last day "
        "of the month set by the time parameter l10n_ca.qc.rl1.due_month, "
        "in the year after the slips. A business cessation brings it to 30 "
        "days after the cessation, and a last periodic remittance to the "
        "20th of the following month, when earlier. A deadline on a "
        "Saturday, a Sunday or a non-business day moves to the next "
        "business day.",
    )
    cessation_date = fields.Date(
        string="Business Cessation Date",
        help="Date the business stopped operating. The RL-1 summary and "
        "slips are then due within 30 days after it.",
    )
    last_remittance_date = fields.Date(
        string="Last Periodic Remittance (No More Employees)",
        help="Date of the last periodic payment of source deductions and "
        "employer contributions, when the employer stops them for good "
        "because it has no more employees. The RL-1 summary and slips are "
        "then due on the 20th of the following month.",
    )
    slip_ids = fields.One2many("l10n_ca.qc.rl1.slip", "summary_id", string="RL-1 Slips")
    remittance_ids = fields.One2many(
        "l10n_ca.qc.payroll.remittance", "summary_id", string="Remittances"
    )
    associated_payroll = fields.Monetary(
        string="Payroll of Associated Employers",
        default=lambda self: self.env.company.l10n_ca_qc_associated_payroll,
        help="Remuneration paid in the year by the employers associated "
        "with the company on December 31, added to line 50.1.",
    )
    training_expenses = fields.Monetary(
        string="Eligible Training Expenditures",
        help="Eligible training expenditures of the year, plus the balance "
        "carried forward (lines 79.1 to 79.3 of the worksheet). Only the "
        "part up to line 73 is used.",
    )
    cnt_paid = fields.Monetary(
        string="Labour Standards Contribution Already Paid",
        help="Line 64: payment of the labour standards contribution already "
        "made for the year.",
    )
    line_21 = fields.Monetary(compute="_compute_lines", store=True)
    line_22 = fields.Monetary(compute="_compute_lines", store=True)
    line_23 = fields.Monetary(compute="_compute_lines", store=True)
    line_24 = fields.Monetary(compute="_compute_lines", store=True)
    line_25 = fields.Monetary(compute="_compute_lines", store=True)
    line_28 = fields.Monetary(compute="_compute_lines", store=True)
    line_29 = fields.Monetary(compute="_compute_lines", store=True)
    line_30 = fields.Monetary(compute="_compute_lines", store=True)
    line_35 = fields.Monetary(compute="_compute_lines", store=True)
    line_38 = fields.Monetary(compute="_compute_lines", store=True)
    line_44 = fields.Monetary(compute="_compute_lines", store=True)
    line_45 = fields.Monetary(compute="_compute_lines", store=True)
    line_46 = fields.Monetary(compute="_compute_lines", store=True)
    line_47 = fields.Monetary(compute="_compute_lines", store=True)
    line_48 = fields.Monetary(compute="_compute_lines", store=True)
    line_50_1 = fields.Monetary(
        string="Line 50.1",
        compute="_compute_lines",
        store=True,
        help="Total payroll that sets the HSF rate: remuneration of all the "
        "done payslips of the year, outside Quebec included, plus the "
        "payroll of the associated employers.",
    )
    line_51 = fields.Monetary(compute="_compute_lines", store=True)
    line_52 = fields.Monetary(
        string="Line 52",
        help="Salaries eligible for a Health Services Fund contribution "
        "credit: subject salaries paid for the exemption period of a major "
        "investment project with the annual certificate of the Minister of "
        "Finance (TP-1015.G part 6.3). They stay in the total payroll of "
        "line 50.1 and are subtracted from line 51 on line 53.",
    )
    line_52_1 = fields.Char(
        string="Line 52.1",
        help="Specification of the HSF contribution credit of line 52.",
    )
    line_53 = fields.Monetary(compute="_compute_lines", store=True)
    line_54 = fields.Float(compute="_compute_lines", store=True, digits=(5, 2))
    line_55 = fields.Monetary(compute="_compute_lines", store=True)
    line_56 = fields.Monetary(compute="_compute_lines", store=True)
    line_57 = fields.Monetary(compute="_compute_lines", store=True)
    line_61 = fields.Monetary(compute="_compute_lines", store=True)
    line_63 = fields.Monetary(compute="_compute_lines", store=True)
    line_64 = fields.Monetary(compute="_compute_lines", store=True)
    line_71 = fields.Monetary(compute="_compute_lines", store=True)
    line_73 = fields.Monetary(compute="_compute_lines", store=True)
    line_74 = fields.Monetary(compute="_compute_lines", store=True)
    line_75 = fields.Monetary(compute="_compute_lines", store=True)
    line_80 = fields.Monetary(compute="_compute_lines", store=True)
    line_81 = fields.Monetary(compute="_compute_lines", store=True)
    line_82 = fields.Monetary(compute="_compute_lines", store=True)
    slip_count = fields.Integer(compute="_compute_lines", store=True)
    hsf_accrued = fields.Monetary(
        string="HSF Accrued on Payslips",
        compute="_compute_lines",
        store=True,
        help="Health Services Fund of the payslips at the estimated rate; "
        "line 57 holds the adjustment to the actual rate.",
    )
    cnesst_insurable = fields.Monetary(
        string="CNESST Insurable Earnings",
        compute="_compute_lines",
        store=True,
        help="Remuneration capped at the maximum insurable earnings per "
        "worker, to report on the CNESST Déclaration des salaires.",
    )
    cnesst_paid = fields.Monetary(
        string="CNESST Periodic Payments",
        compute="_compute_lines",
        store=True,
    )
    csv_file = fields.Binary(string="CSV File", attachment=False, readonly=True)
    csv_filename = fields.Char()

    _sql_constraints = [
        (
            "company_year_unique",
            "unique (company_id, year)",
            "A company has one RL-1 summary per year.",
        ),
    ]

    @api.depends("year")
    def _compute_name(self):
        for summary in self:
            summary.name = _("RL-1 Summary %(year)s", year=summary.year)

    @api.depends("year", "company_id", "cessation_date", "last_remittance_date")
    def _compute_due_date(self):
        """Earliest deadline of the RLZ-1.S, moved to a business day.

        The last day of month l10n_ca.qc.rl1.due_month of the following
        year; 30 days after ``cessation_date``; the 20th of the month after
        ``last_remittance_date``. The earliest one moves to the next
        business day of Revenu Quebec (TP-1015.G part 11.3).
        """
        Remittance = self.env["l10n_ca.qc.payroll.remittance"]
        for summary in self:
            if not summary.year:
                summary.due_date = False
                continue
            following = summary.year + 1
            month = int(
                summary.company_id._l10n_ca_param(
                    "l10n_ca.qc.rl1.due_month", Date(following, 1, 1), default=2
                )
            )
            deadlines = [
                Date(following, month, calendar.monthrange(following, month)[1])
            ]
            if summary.cessation_date:
                deadlines.append(summary.cessation_date + timedelta(days=30))
            if summary.last_remittance_date:
                deadlines.append(
                    summary.last_remittance_date + relativedelta(months=1, day=20)
                )
            summary.due_date = Remittance._l10n_ca_qc_next_business_day(
                summary.company_id, min(deadlines)
            )

    def _l10n_ca_qc_year_payslips(self, quebec=True):
        """Return the done payslips of the year, by default those in Quebec."""
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            ("l10n_ca_pay_date", ">=", Date(self.year, 1, 1)),
            ("l10n_ca_pay_date", "<=", Date(self.year, 12, 31)),
        ]
        if quebec:
            domain.append(("l10n_ca_province_id.code", "=", "QC"))
        return self.env["hr.payslip"].search(domain)

    @api.depends(
        "year",
        "company_id",
        "associated_payroll",
        "line_52",
        "training_expenses",
        "cnt_paid",
        "slip_ids.box_a",
        "slip_ids.box_b_a",
        "slip_ids.box_b_b",
        "slip_ids.box_e",
        "slip_ids.box_h",
        "slip_ids.box_i",
        "slip_ids.cnt_base",
        "slip_ids.hsf",
        "slip_ids.cnesst_base",
        "remittance_ids.qpp",
        "remittance_ids.qpip",
        "remittance_ids.income_tax",
        "remittance_ids.hsf",
        "remittance_ids.cnesst",
    )
    def _compute_lines(self):
        """Lines of the RL-1 summary per the RLZ-1.S guide.

        Line 29 is the eligible salary of box I times the employer QPIP
        rate of the year; line 54 is the HSF rate of the actual total
        payroll (line 50.1), applied on line 55 to the subject salaries
        less the salaries eligible for an HSF credit (line 53 = 51 - 52).
        Lines 44 to 46 and 56 are the amounts of the
        remittances of the year. Line 80 adds the balances 48 and 57, the
        unpaid labour standards contribution and the WSDRF contribution.
        """
        for summary in self:
            slips = summary.slip_ids
            company = summary.company_id
            year_end = Date(summary.year or 2000, 12, 31)
            currency = summary.currency_id

            def total(name, records=slips):
                return sum(records.mapped(name))

            vals = dict.fromkeys(_COMPUTED_LINES, 0.0)
            vals["slip_count"] = len(slips)
            if not summary.year or not company:
                summary.update(vals)
                continue
            param = company._l10n_ca_param
            vals["line_21"] = vals["line_22"] = total("box_b_a")
            vals["line_23"] = vals["line_24"] = total("box_b_b")
            vals["line_25"] = 2 * (vals["line_21"] + vals["line_23"])
            vals["line_28"] = total("box_h")
            employer_rate = param("l10n_ca.qpip.employer_rate", year_end, default=0.0)
            vals["line_29"] = currency.round(total("box_i") * employer_rate)
            vals["line_30"] = vals["line_28"] + vals["line_29"]
            vals["line_35"] = total("box_e")
            vals["line_38"] = vals["line_25"] + vals["line_30"] + vals["line_35"]
            remittances = summary.remittance_ids
            vals["line_44"] = total("qpp", remittances)
            vals["line_45"] = total("qpip", remittances)
            vals["line_46"] = total("income_tax", remittances)
            vals["line_47"] = vals["line_44"] + vals["line_45"] + vals["line_46"]
            vals["line_48"] = currency.round(vals["line_38"] - vals["line_47"])

            all_slips = summary._l10n_ca_qc_year_payslips(quebec=False)
            vals["line_50_1"] = (
                all_slips._l10n_ca_line_totals()["GROSS"] + summary.associated_payroll
            )
            vals["line_51"] = total("box_a")
            vals["line_54"] = (
                company._l10n_ca_qc_hsf_rate(vals["line_50_1"], year_end)
                if slips
                else 0.0
            )
            vals["line_53"] = max(vals["line_51"] - summary.line_52, 0.0)
            vals["line_55"] = currency.round(vals["line_53"] * vals["line_54"] / 100)
            vals["line_56"] = total("hsf", remittances)
            vals["line_57"] = currency.round(vals["line_55"] - vals["line_56"])
            vals["hsf_accrued"] = total("hsf")

            vals["line_61"] = total("cnt_base")
            vals["line_63"] = currency.round(
                vals["line_61"] * param("l10n_ca.qc.cnt.rate", year_end, default=0.0)
            )
            vals["line_64"] = summary.cnt_paid

            threshold = param(
                "l10n_ca.qc.wsdrf.payroll_threshold", year_end, default=None
            )
            payroll = vals["line_51"]
            if threshold is not None and payroll > threshold:
                vals["line_71"] = payroll
                vals["line_73"] = currency.round(
                    payroll * param("l10n_ca.qc.wsdrf.rate", year_end)
                )
            else:
                vals["line_71"] = vals["line_73"] = 0.0
            vals["line_74"] = min(summary.training_expenses, vals["line_73"])
            vals["line_75"] = vals["line_73"] - vals["line_74"]

            balance = currency.round(
                vals["line_48"]
                + vals["line_57"]
                + vals["line_63"]
                - vals["line_64"]
                + vals["line_75"]
            )
            vals["line_80"] = balance
            vals["line_81"] = -balance if balance < 0 else 0.0
            vals["line_82"] = balance if balance > 0 else 0.0
            vals["cnesst_insurable"] = total("cnesst_base")
            vals["cnesst_paid"] = total("cnesst", remittances)
            summary.update(vals)

    def action_compute_slips(self):
        """Rebuild the RL-1 slips from the done payslips of the year.

        One slip per employee who worked in Quebec during the year.
        """
        Slip = self.env["l10n_ca.qc.rl1.slip"]
        for summary in self:
            summary.slip_ids.unlink()
            groups = defaultdict(lambda: self.env["hr.payslip"])
            for payslip in summary._l10n_ca_qc_year_payslips():
                groups[payslip.employee_id] |= payslip
            vals_list = []
            for employee, payslips in groups.items():
                vals = {
                    "summary_id": summary.id,
                    "employee_id": employee.id,
                    "payslip_ids": [(6, 0, payslips.ids)],
                }
                vals.update(payslips._l10n_ca_qc_rl1_values(summary.year))
                vals_list.append(vals)
            Slip.create(vals_list)
        return True

    def action_compute_remittances(self):
        Remittance = self.env["l10n_ca.qc.payroll.remittance"]
        for summary in self:
            Remittance._l10n_ca_qc_generate(summary.company_id, summary.year, summary)
        return True

    def _l10n_ca_qc_rl1_csv_rows(self):
        """Rows of the RL-1 export: one row per slip, then the summary lines.

        Amounts have two decimals and no thousands separator, to type them
        in the online RL-1 service of Revenu Quebec. Headers and labels are
        in the language of the environment.
        """
        self.ensure_one()
        tr = self.env._
        header = [
            tr("Employee"),
            tr("SIN"),
            tr("Slip code"),
            *[tr(label) for _field, label in RL1_BOXES],
        ]
        rows = [header]
        for slip in self.slip_ids.sorted(lambda s: s.employee_id.name or ""):
            rows.append(
                [
                    slip.employee_id.name,
                    slip.sin or "",
                    slip.slip_code,
                    *[_amount(slip[name]) for name, _label in RL1_BOXES],
                ]
            )
        rows.append([])
        rows.append(
            [
                tr("RL-1 Summary"),
                str(self.year),
                self.company_id.l10n_ca_qc_rq_account_number or "",
                self.company_id.l10n_ca_neq or "",
            ]
        )
        for name, label in SUMMARY_LINES:
            value = self[name]
            rows.append(
                [tr(label), f"{value:.2f}" if isinstance(value, float) else value or ""]
            )
        rows.append([tr("Number of RL-1 slips"), self.slip_count])
        return rows

    def _l10n_ca_qc_remittance_csv_rows(self):
        """Rows of the remittance export, headers in the language of the
        environment."""
        self.ensure_one()
        tr = self.env._
        fields_order = [
            ("date_from", tr("Paid from")),
            ("date_to", tr("Paid to")),
            ("due_date", tr("Due date")),
            ("gross_payroll", tr("Gross payroll")),
            ("qpp", tr("QPP")),
            ("qpip", tr("QPIP")),
            ("income_tax", tr("Quebec income tax")),
            ("hsf", tr("Health services fund")),
            ("cnesst", tr("CNESST")),
            ("total", tr("Total")),
            ("amount_paid", tr("Amount paid")),
            ("payment_date", tr("Payment date")),
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

    def _l10n_ca_qc_download(self, rows, filename):
        self.ensure_one()
        self.write({"csv_file": _csv_file(rows), "csv_filename": filename})
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self._name}/{self.id}/csv_file/{filename}"
            "?download=true",
            "target": "self",
        }

    def action_export_rl1_csv(self):
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(_("Compute the RL-1 slips before exporting them."))
        return self._l10n_ca_qc_download(
            self._l10n_ca_qc_rl1_csv_rows(), f"RL-1_{self.year}.csv"
        )

    def action_export_remittance_csv(self):
        self.ensure_one()
        if not self.remittance_ids:
            raise UserError(_("Compute the remittances before exporting them."))
        return self._l10n_ca_qc_download(
            self._l10n_ca_qc_remittance_csv_rows(),
            f"TPZ-1015.R.14_{self.year}.csv",
        )


class L10nCaQcRl1Slip(models.Model):
    _name = "l10n_ca.qc.rl1.slip"
    _description = "RL-1 Slip"
    _order = "summary_id, employee_id"

    summary_id = fields.Many2one(
        "l10n_ca.qc.rl1.summary",
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
    slip_code = fields.Selection(
        [("R", "R - Original"), ("A", "A - Amended"), ("D", "D - Cancelled")],
        default="R",
        required=True,
        help="Code du relevé: R for an original slip, A for an amended slip, "
        "D for a cancelled slip.",
    )
    payslip_ids = fields.Many2many("hr.payslip", string="Payslips")
    box_a = fields.Monetary(string="Box A - Employment Income")
    box_b_a = fields.Monetary(string="Box B.A - QPP Contribution")
    box_b_b = fields.Monetary(string="Box B.B - Additional QPP Contribution")
    box_c = fields.Monetary(string="Box C - EI Premium")
    box_e = fields.Monetary(string="Box E - Quebec Income Tax Withheld")
    box_f = fields.Monetary(string="Box F - Union Dues")
    box_g = fields.Monetary(string="Box G - Pensionable Salary under the QPP")
    box_h = fields.Monetary(string="Box H - QPIP Premium")
    box_i = fields.Monetary(string="Box I - Eligible Salary under the QPIP")
    employer_qpp = fields.Monetary(string="Employer QPP")
    employer_qpp2 = fields.Monetary(string="Employer QPP2")
    employer_qpip = fields.Monetary(string="Employer QPIP")
    hsf = fields.Monetary(string="Health Services Fund")
    cnt = fields.Monetary(string="Labour Standards Contribution")
    cnt_base = fields.Monetary(string="Remuneration Subject to the CNT")
    cnesst = fields.Monetary(string="CNESST Premium")
    cnesst_base = fields.Monetary(string="CNESST Insurable Earnings")
    wsdrf = fields.Monetary(string="WSDRF Accrued")

    @api.depends("employee_id")
    def _compute_sin(self):
        for slip in self:
            slip.sin = slip.employee_id.ssnid
