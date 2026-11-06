# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import io
import zipfile
from datetime import date

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..hooks import l10n_ca_load_report_line_terms, l10n_ca_tag_line_101


@tagged("post_install", "-at_install")
class TestTaxReturn(AccountTestInvoicingCommon):
    """Returns of a Quebec company on the ca_2023 chart.

    First quarter of 2026, posted in setUpClass:
    - invoice 1,000 GST+QST: GST 50.00, QST 99.75 (total 1,149.75)
    - invoice 2,000 GST only: GST 100.00
    - invoice 3,000 zero-rated export (0% Int): no tax
    - bill 400 GST+QST: GST 20.00, QST 39.90
    - credit note 200 GST+QST: GST 10.00, QST 19.95
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ca")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.state_id = cls.env.ref("base.state_ca_qc")
        chart = cls.env["account.chart.template"].with_company(cls.company)
        cls.gst_sale = chart.ref("gst_sale_tax_5")
        cls.gstqst_sale = chart.ref("gstqst_sale_tax_14975")
        cls.int_sale = chart.ref("int_sale_tax_0")
        cls.gstqst_purchase = chart.ref("gstqst_purchase_tax_14975")
        cls.account_gst = chart.ref("l10n_ca_231000")
        cls.account_qst = chart.ref("l10n_ca_232000")
        cls.account_gst_itc = chart.ref("l10n_ca_118100")
        cls.account_qst_itc = chart.ref("l10n_ca_118200")
        cls.account_authority = chart.ref("l10n_ca_221210")
        cls.account_gain = chart.ref("l10n_ca_413300")
        cls.account_capital = cls.env["account.account"].search(
            [
                *cls.env["account.account"]._check_company_domain(cls.company),
                ("account_type", "=", "asset_fixed"),
            ],
            limit=1,
        )
        cls.account_bad_debt = cls.company_data["default_account_expense"]
        cls.company.l10n_ca_bad_debt_account_id = cls.account_bad_debt
        q1 = date(2026, 2, 15)
        cls.inv_gstqst = cls._invoice("out_invoice", q1, [(1000, cls.gstqst_sale)])
        cls._invoice("out_invoice", q1, [(2000, cls.gst_sale)])
        cls._invoice("out_invoice", q1, [(3000, cls.int_sale)])
        cls._invoice("in_invoice", q1, [(400, cls.gstqst_purchase)])
        cls._invoice("out_refund", q1, [(200, cls.gstqst_sale)])

    @classmethod
    def _invoice(cls, move_type, invoice_date, lines):
        move = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": cls.partner_a.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": [Command.set(tax.ids)],
                            **({"account_id": line[2].id} if len(line) > 2 else {}),
                        }
                    )
                    for line in lines
                    for amount, tax in [line[:2]]
                ],
            }
        )
        move.action_post()
        return move

    def _return(self, kind, date_from, date_to, method="regular"):
        tax_return = self.env["l10n.ca.tax.return"].create(
            {
                "company_id": self.company.id,
                "kind": kind,
                "date_from": date_from,
                "date_to": date_to,
                "method": method,
            }
        )
        tax_return.action_compute()
        return tax_return

    def _lines(self, tax_return):
        return {line.code: line.amount for line in tax_return.line_ids}

    def _period_balance(self, account, date_from, date_to):
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("parent_state", "=", "posted"),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ]
        )
        return sum(lines.mapped("balance"))

    # ------------------------------------------------------------------

    def test_gst34_regular(self):
        # 90 = 1,000 + 2,000 - 200; 91 = export 3,000; 101 = 90 + 91.
        # 103 = 50 + 100 - 10 = 140; 106 = 20; 109 = 140 - 20 = 120.
        ret = self._return("gst_hst", date(2026, 1, 1), date(2026, 3, 31))
        lines = self._lines(ret)
        self.assertAlmostEqual(lines["90"], 2800.0)
        self.assertAlmostEqual(lines["91"], 3000.0)
        self.assertAlmostEqual(lines["101"], 5800.0)
        self.assertAlmostEqual(lines["103"], 140.0)
        self.assertAlmostEqual(lines["105"], 140.0)
        self.assertAlmostEqual(lines["106"], 20.0)
        self.assertAlmostEqual(lines["108"], 20.0)
        self.assertAlmostEqual(lines["109"], 120.0)
        self.assertAlmostEqual(lines["115"], 120.0)
        self.assertAlmostEqual(lines["114"], 0.0)
        self.assertAlmostEqual(ret.net_tax, 120.0)
        self.assertAlmostEqual(ret.amount_due, 120.0)
        # Quarterly filer: due one month after the end of the period.
        self.company.l10n_ca_gst_filing_frequency = "quarterly"
        ret.invalidate_recordset(["date_due"])
        ret._compute_date_due()
        self.assertEqual(ret.date_due, date(2026, 4, 30))
        # A period ending on a month end is due on the last day of the
        # target month: June 30 + 1 month = July 31, not July 30.
        ret.write({"date_from": date(2026, 4, 1), "date_to": date(2026, 6, 30)})
        self.assertEqual(ret.date_due, date(2026, 7, 31))
        # Annual filer: three months after the fiscal year end.
        self.company.l10n_ca_gst_filing_frequency = "annual"
        ret.write({"date_from": date(2025, 1, 1), "date_to": date(2025, 12, 31)})
        self.assertEqual(ret.date_due, date(2026, 3, 31))

    def test_fpz500_regular(self):
        # 101 includes the export once the 0% Int tax carries CaQc101:
        # 2,800 + 3,000. 203 = 99.75 - 19.95 = 79.80; 206 = 39.90.
        ret = self._return("qst", date(2026, 1, 1), date(2026, 3, 31))
        lines = self._lines(ret)
        self.assertAlmostEqual(lines["101"], 5800.0)
        self.assertAlmostEqual(lines["103"], 140.0)
        self.assertAlmostEqual(lines["203"], 79.80)
        self.assertAlmostEqual(lines["106"], 20.0)
        self.assertAlmostEqual(lines["206"], 39.90)
        self.assertAlmostEqual(lines["109"], 120.0)
        self.assertAlmostEqual(lines["209"], 39.90)
        self.assertAlmostEqual(lines["116"], 120.0)
        self.assertAlmostEqual(lines["216"], 39.90)
        self.assertAlmostEqual(ret.net_tax, 159.90)
        # Line 101 is informational: the net tax ignores it.
        self.assertAlmostEqual(ret.net_tax, lines["109"] + lines["209"])
        # A line with a value in both columns names its column; a line with
        # one value does not.
        names = {
            line.code: line.name for line in ret.with_context(lang="en_US").line_ids
        }
        self.assertTrue(names["103"].endswith("(GST/HST)"), names["103"])
        self.assertTrue(names["203"].endswith("(QST)"), names["203"])
        self.assertNotIn("(", names["101"])

    def test_line_101_hook_on_existing_company(self):
        country = self.env.ref("base.ca")
        tags = self.env["account.account.tag"]._get_tax_tags("CaQc101", country.id)
        self.int_sale.repartition_line_ids.tag_ids -= tags
        export_line = self.env["account.move.line"].search(
            [("tax_ids", "in", self.int_sale.ids), ("company_id", "=", self.company.id)]
        )
        export_line.tax_tag_ids -= tags
        ret = self._return("qst", date(2026, 1, 1), date(2026, 3, 31))
        self.assertAlmostEqual(self._lines(ret)["101"], 2800.0)
        count = l10n_ca_tag_line_101(self.env, self.company)
        self.assertEqual(count, 1)
        base = self.int_sale.repartition_line_ids.filtered(
            lambda r: r.repartition_type == "base"
        )
        self.assertTrue(all(r.tag_ids & tags for r in base))
        ret.action_compute()
        self.assertAlmostEqual(self._lines(ret)["101"], 5800.0)
        self.assertAlmostEqual(ret.net_tax, 159.90)

    def test_line_101_hook_respects_lock_dates(self):
        # A posted item on or before any lock date keeps its tags: the hook
        # skips it instead of failing on the lock date check.
        country = self.env.ref("base.ca")
        tags = self.env["account.account.tag"]._get_tax_tags("CaQc101", country.id)
        self.int_sale.repartition_line_ids.tag_ids -= tags
        export_line = self.env["account.move.line"].search(
            [("tax_ids", "in", self.int_sale.ids), ("company_id", "=", self.company.id)]
        )
        export_line.tax_tag_ids -= tags
        self.company.fiscalyear_lock_date = date(2026, 2, 28)
        self.assertEqual(l10n_ca_tag_line_101(self.env, self.company), 0)
        self.assertFalse(export_line.tax_tag_ids & tags)
        base = self.int_sale.repartition_line_ids.filtered(
            lambda r: r.repartition_type == "base"
        )
        self.assertTrue(all(r.tag_ids & tags for r in base))

    def test_closing_zeroes_tax_accounts(self):
        start, end = date(2026, 1, 1), date(2026, 3, 31)
        ret = self._return("qst", start, end)
        ret.action_close()
        self.assertEqual(ret.state, "closed")
        self.assertEqual(ret.closing_move_id.state, "posted")
        for account in (
            self.account_gst,
            self.account_qst,
            self.account_gst_itc,
            self.account_qst_itc,
        ):
            self.assertAlmostEqual(self._period_balance(account, start, end), 0.0)
        # 140 + 79.80 - 20 - 39.90 owed to Revenu Quebec.
        self.assertAlmostEqual(
            self._period_balance(self.account_authority, start, end), -159.90
        )
        with self.assertRaises(UserError):
            self._return("gst_hst", start, end).action_close()
        ret.action_mark_filed()
        self.assertEqual(ret.state, "filed")
        ret.action_reset_to_draft()
        self.assertFalse(ret.closing_move_id)
        self.assertAlmostEqual(
            self._period_balance(self.account_gst, start, end), -140.0
        )

    def test_reset_cancels_undeletable_closing(self):
        # Under the restrictive audit trail a posted entry cannot be
        # deleted: resetting the return cancels its closing entry, which
        # leaves the tax accounts as they were before the closing.
        start, end = date(2026, 1, 1), date(2026, 3, 31)
        self.company.check_account_audit_trail = True
        ret = self._return("qst", start, end)
        ret.action_close()
        move = ret.closing_move_id
        ret.action_reset_to_draft()
        self.assertEqual(ret.state, "draft")
        self.assertFalse(ret.closing_move_id)
        self.assertEqual(move.state, "cancel")
        self.assertAlmostEqual(
            self._period_balance(self.account_gst, start, end), -140.0
        )
        self.assertAlmostEqual(
            self._period_balance(self.account_authority, start, end), 0.0
        )
        # The return computes and closes again.
        ret.action_compute()
        ret.action_close()
        self.assertEqual(ret.closing_move_id.state, "posted")

    def test_due_date_follows_the_period(self):
        # The deadline of a return depends on its own period, not on the
        # filing frequency the company has today.
        self.company.l10n_ca_gst_filing_frequency = "annual"
        ret = self._return("gst_hst", date(2026, 1, 1), date(2026, 3, 31))
        self.assertEqual(ret.date_due, date(2026, 4, 30))
        ret.write({"date_from": date(2025, 1, 1), "date_to": date(2025, 12, 31)})
        self.assertEqual(ret.date_due, date(2026, 3, 31))
        self.company.l10n_ca_gst_filing_frequency = "quarterly"
        ret.invalidate_recordset(["date_due"])
        ret._compute_date_due()
        self.assertEqual(ret.date_due, date(2026, 3, 31))

    def test_quick_method(self):
        """Second quarter under the quick method, services, Quebec.

        Sales 28,000 GST+QST (GST 1,400, QST 2,793), export 5,000, computer
        2,000 on a fixed asset (GST 100, QST 199.50), expense 1,000 (GST 50,
        QST 99.75).
        GST: eligible 29,400 x 3.6% = 1,058.40. Credit: the first quarter
        used 1,050 + 2,100 - 210 = 2,940 of the 30,000, so
        1% x min(29,400, 27,060) = 270.60. ITC on capital only: 100.
        109 = 1,058.40 - (100 + 270.60) = 687.80.
        QST: eligible 30,793 x 6.6% = 2,032.338 -> 2,032.34. Credit: first
        quarter used 1,099.75 - 219.95 = 879.80 of 31,421, so
        1% x min(30,793, 30,541.20) = 305.41. 209 = 2,032.34 - 199.50 -
        305.41 = 1,527.43.
        Books: 1,400 - 150 + 2,793 - 299.25 = 3,743.75, gain = 3,743.75 -
        (687.80 + 1,527.43) = 1,528.52.
        101 = supplies 28,000 + export 5,000 + the GST/HST charged, 1,400 =
        34,400: the FPZ-500 includes the GST/HST in line 101 under the quick
        method, not the QST.
        """
        self.company.write(
            {
                "l10n_ca_quick_method": True,
                "l10n_ca_quick_method_date": date(2026, 1, 1),
                "l10n_ca_quick_method_activity": "service",
            }
        )
        q2 = date(2026, 5, 10)
        self._invoice("out_invoice", q2, [(28000, self.gstqst_sale)])
        self._invoice("out_invoice", q2, [(5000, self.int_sale)])
        self._invoice(
            "in_invoice", q2, [(2000, self.gstqst_purchase, self.account_capital)]
        )
        self._invoice("in_invoice", q2, [(1000, self.gstqst_purchase)])
        start, end = date(2026, 4, 1), date(2026, 6, 30)
        ret = self._return("qst", start, end, method="quick")
        lines = self._lines(ret)
        self.assertAlmostEqual(lines["101"], 34400.0)
        self.assertAlmostEqual(lines["103"], 1058.40)
        self.assertAlmostEqual(lines["106"], 100.0)
        self.assertAlmostEqual(lines["107"], 270.60)
        self.assertAlmostEqual(lines["109"], 687.80)
        self.assertAlmostEqual(lines["203"], 2032.34)
        self.assertAlmostEqual(lines["206"], 199.50)
        self.assertAlmostEqual(lines["207"], 305.41)
        self.assertAlmostEqual(lines["209"], 1527.43)
        self.assertAlmostEqual(ret.net_tax, 2215.23)
        self.assertAlmostEqual(ret.regular_net_tax, 3743.75)
        self.assertAlmostEqual(ret.quick_method_gain, 1528.52)
        ret.action_close()
        for account in (
            self.account_gst,
            self.account_qst,
            self.account_gst_itc,
            self.account_qst_itc,
        ):
            self.assertAlmostEqual(self._period_balance(account, start, end), 0.0)
        self.assertAlmostEqual(
            self._period_balance(self.account_authority, start, end), -2215.23
        )
        self.assertAlmostEqual(
            self._period_balance(self.account_gain, start, end), -1528.52
        )

    def test_quick_method_capital_sale(self):
        """Third quarter under the quick method, services, Quebec.

        One invoice: services 4,000 and a vehicle 10,000 on a fixed asset
        account, both GST+QST: GST 700, QST 1,396.50. The sale of capital
        property is not an eligible supply: its tax, 10/14 of each tax
        line (GST 500, QST 997.50), is remitted in full.
        GST: eligible (14,000 + 700) x 4/14 = 4,200 x 3.6% = 151.20,
        103 = 151.20 + 500 = 651.20. Credit: the first quarter used 2,940
        of the 30,000, so 1% x 4,200 = 42.00; 109 = 651.20 - 42 = 609.20.
        QST: eligible (14,000 + 1,396.50) x 4/14 = 4,399 x 6.6% = 290.334
        -> 290.33, 203 = 290.33 + 997.50 = 1,287.83. Credit 1% x 4,399 =
        43.99; 209 = 1,287.83 - 43.99 = 1,243.84.
        101 = 14,000 + GST 700 = 14,700. Books 700 + 1,396.50 = 2,096.50,
        gain = 2,096.50 - (609.20 + 1,243.84) = 243.46.
        """
        self.company.write(
            {
                "l10n_ca_quick_method": True,
                "l10n_ca_quick_method_date": date(2026, 1, 1),
                "l10n_ca_quick_method_activity": "service",
            }
        )
        self._invoice(
            "out_invoice",
            date(2026, 8, 10),
            [
                (4000, self.gstqst_sale),
                (10000, self.gstqst_sale, self.account_capital),
            ],
        )
        start, end = date(2026, 7, 1), date(2026, 9, 30)
        ret = self._return("qst", start, end, method="quick")
        lines = self._lines(ret)
        self.assertAlmostEqual(lines["101"], 14700.0)
        self.assertAlmostEqual(lines["103"], 651.20)
        self.assertAlmostEqual(lines["107"], 42.0)
        self.assertAlmostEqual(lines["109"], 609.20)
        self.assertAlmostEqual(lines["203"], 1287.83)
        self.assertAlmostEqual(lines["207"], 43.99)
        self.assertAlmostEqual(lines["209"], 1243.84)
        self.assertAlmostEqual(ret.regular_net_tax, 2096.50)
        self.assertAlmostEqual(ret.quick_method_gain, 243.46)
        # The note is written in the language of the reader: amounts are
        # matched whatever the separators of that language.
        self.assertRegex(ret.quick_method_note, "4(,|\u00a0|\u202f| )200[.,]00")
        self.assertRegex(ret.quick_method_note, "997[.,]50")
        # The GST34 shares the computation: 101 is the eligible 4,200.
        gst34 = self._lines(self._return("gst_hst", start, end, method="quick"))
        self.assertAlmostEqual(gst34["101"], 4200.0)
        self.assertAlmostEqual(gst34["103"], 651.20)
        self.assertAlmostEqual(gst34["107"], 42.0)

    def test_quick_method_threshold_zero_rated(self):
        """Previous fiscal year: sales 350,000 GST+QST and exports 50,000.

        GST: 367,500 tax-included + 50,000 zero-rated = 417,500 > 400,000.
        QST: 384,912.50 tax-included + 50,000 zero-rated = 434,912.50 >
        418,952. Without the exports, neither total exceeds its threshold.
        """
        self.company.write(
            {
                "l10n_ca_quick_method": True,
                "l10n_ca_quick_method_date": date(2026, 1, 1),
            }
        )
        previous = date(2025, 6, 15)
        self._invoice("out_invoice", previous, [(350000, self.gstqst_sale)])
        ret = self._return("qst", date(2026, 1, 1), date(2026, 3, 31), "quick")
        self.assertNotRegex(ret.quick_method_note, "367(,| | | )500")
        self._invoice("out_invoice", previous, [(50000, self.int_sale)])
        ret.action_compute()
        # The note is written in the language of the reader: amounts are
        # matched whatever the separators of that language.
        self.assertRegex(ret.quick_method_note, "417(,| | | )500[.,]00")
        self.assertRegex(ret.quick_method_note, "434(,| | | )912[.,]50")

    def test_quick_method_gst34(self):
        # GST34 under the quick method: 101 = tax-included eligible supplies
        # of the first quarter, 2,940; 103 = 2,940 x 3.6% = 105.84; credit
        # 1% x 2,940 = 29.40 on 107; no ITC on the non-capital bill.
        # Lines 90 and 91 are not part of a quick method return.
        self.company.l10n_ca_quick_method = True
        ret = self._return(
            "gst_hst", date(2026, 1, 1), date(2026, 3, 31), method="quick"
        )
        lines = self._lines(ret)
        self.assertNotIn("90", lines)
        self.assertAlmostEqual(lines["101"], 2940.0)
        self.assertAlmostEqual(lines["103"], 105.84)
        self.assertAlmostEqual(lines["106"], 0.0)
        self.assertAlmostEqual(lines["107"], 29.40)
        self.assertAlmostEqual(lines["109"], 76.44)

    def test_bad_debt_write_off_and_recovery(self):
        """Write-off of 749.75 of a 1,149.75 invoice, then recovery of 100.

        GST = 749.75 x 50 / 1,149.75 = 32.60, QST = 749.75 x 99.75 /
        1,149.75 = 65.05, expense 749.75 - 97.65 = 652.10. Recovery of 100:
        GST = 100 x 50 / 1,149.75 = 4.35, QST = 100 x 99.75 / 1,149.75 =
        8.68.
        """
        q3 = date(2026, 8, 1)
        invoice = self._invoice("out_invoice", q3, [(1000, self.gstqst_sale)])
        wizard = self.env["l10n.ca.bad.debt.wizard"].create(
            {"move_id": invoice.id, "date": date(2026, 8, 20)}
        )
        self.assertAlmostEqual(wizard.amount, 1149.75)
        self.assertAlmostEqual(wizard.gst_amount, 50.0)
        self.assertAlmostEqual(wizard.qst_amount, 99.75)
        wizard.amount = 749.75
        self.assertAlmostEqual(wizard.gst_amount, 32.60)
        self.assertAlmostEqual(wizard.qst_amount, 65.05)
        wizard.action_confirm()
        self.assertAlmostEqual(invoice.amount_residual, 400.0)
        self.assertAlmostEqual(invoice.l10n_ca_bad_debt_written_off, 749.75)
        self.assertAlmostEqual(
            self._period_balance(
                self.account_bad_debt, date(2026, 8, 20), date(2026, 8, 31)
            ),
            652.10,
        )
        with self.assertRaises(UserError):
            self.env["l10n.ca.bad.debt.wizard"].create(
                {"move_id": invoice.id, "amount": 400.01}
            ).action_confirm()
        recovery = self.env["l10n.ca.bad.debt.wizard"].create(
            {
                "move_id": invoice.id,
                "operation": "recovery",
                "amount": 100.0,
                "date": date(2026, 9, 5),
            }
        )
        recovery.action_confirm()
        self.assertAlmostEqual(invoice.l10n_ca_bad_debt_recovered, 100.0)
        with self.assertRaises(UserError):
            self.env["l10n.ca.bad.debt.wizard"].create(
                {
                    "move_id": invoice.id,
                    "operation": "recovery",
                    "amount": 700.0,
                }
            ).action_confirm()
        start, end = date(2026, 7, 1), date(2026, 9, 30)
        fpz = self._lines(self._return("qst", start, end))
        self.assertAlmostEqual(fpz["103"], 50.0)
        self.assertAlmostEqual(fpz["104"], 4.35)
        self.assertAlmostEqual(fpz["107"], 32.60)
        self.assertAlmostEqual(fpz["109"], 50.0 + 4.35 - 32.60)
        self.assertAlmostEqual(fpz["203"], 99.75)
        self.assertAlmostEqual(fpz["204"], 8.68)
        self.assertAlmostEqual(fpz["207"], 65.05)
        self.assertAlmostEqual(fpz["209"], 99.75 + 8.68 - 65.05)
        gst34 = self._lines(self._return("gst_hst", start, end))
        self.assertAlmostEqual(gst34["104"], 4.35)
        self.assertAlmostEqual(gst34["107"], 32.60)
        # The adjustments sit in the tax accounts, so the closing balances.
        ret = self.env["l10n.ca.tax.return"].search(
            [("kind", "=", "qst"), ("date_from", "=", start)]
        )
        ret.action_close()
        self.assertAlmostEqual(self._period_balance(self.account_gst, start, end), 0.0)
        self.assertAlmostEqual(self._period_balance(self.account_qst, start, end), 0.0)

    def test_zero_period_and_reports(self):
        ret = self._return("qst", date(2025, 1, 1), date(2025, 3, 31))
        self.assertTrue(ret.line_ids)
        self.assertFalse(any(ret.line_ids.mapped("amount")))
        ret.action_close()
        self.assertEqual(ret.state, "closed")
        self.assertFalse(ret.closing_move_id)
        q1 = self._return("gst_hst", date(2026, 1, 1), date(2026, 3, 31))
        # The PDF is in the language of the company: English is forced, the
        # database may have another language installed.
        self.company.partner_id.lang = "en_US"
        html = self.env["ir.actions.report"]._render_qweb_html(
            "l10n_ca_tax_return.action_report_tax_return", q1.ids
        )[0]
        self.assertIn(b"Sales and other revenues", html)
        content, ext = (
            self.env["ir.actions.report"]
            .with_context(lang="en_US")
            ._render_xlsx(
                "l10n_ca_tax_return.action_report_tax_return_xlsx", q1.ids, {}
            )
        )
        self.assertEqual(ext, "xlsx")
        self.assertTrue(content.startswith(b"PK"))
        self.assertIn("Business number", self._xlsx_strings(content))

    @staticmethod
    def _xlsx_strings(content):
        """Return the shared strings of an XLSX file, as one text."""
        with zipfile.ZipFile(io.BytesIO(content)) as workbook:
            return workbook.read("xl/sharedStrings.xml").decode()

    def test_reports_in_french(self):
        # The XLSX and the quick method note read in the language of the
        # reader, amounts formatted in that language. Quick method credit
        # base of the first quarter: GST 2,940.00, QST 879.80.
        self.env["res.lang"]._activate_lang("fr_CA")
        self.env["ir.module.module"]._load_module_terms(
            ["l10n_ca", "l10n_ca_tax_return"], ["fr_CA"], overwrite=True
        )
        self.company.l10n_ca_quick_method = True
        ret = self._return("qst", date(2026, 1, 1), date(2026, 3, 31), method="quick")
        ret = ret.with_context(lang="fr_CA")
        ret.action_compute()
        note = ret.quick_method_note
        self.assertIn("TPS/TVH :", note)
        self.assertIn("TVQ :", note)
        self.assertNotIn("GST/HST", note)
        self.assertIn("940,00", note)
        self.assertIn("879,80", note)
        content = (
            self.env["ir.actions.report"]
            .with_context(lang="fr_CA")
            ._render_xlsx(
                "l10n_ca_tax_return.action_report_tax_return_xlsx", ret.ids, {}
            )[0]
        )
        strings = self._xlsx_strings(content)
        for label in ("Société", "Statut", "Méthode rapide", "(TVQ)"):
            self.assertIn(label, strings)
        self.assertNotIn("Business number", strings)

    def test_fpz500_line_names_in_french(self):
        # The French names of the FPZ-500 lines come from this module, over
        # the l10n_ca ones: line 108/208 is the total of lines 106 and 107.
        self.env["res.lang"]._activate_lang("fr_CA")
        self.env["ir.module.module"]._load_module_terms(
            ["l10n_ca"], ["fr_CA"], overwrite=True
        )
        report_line = self.env.ref("l10n_ca.l10n_ca_tr_qst_108_208")
        self.assertNotIn("Total des CTI", report_line.with_context(lang="fr_CA").name)
        l10n_ca_load_report_line_terms(self.env)
        self.env.invalidate_all()
        self.assertEqual(
            report_line.with_context(lang="fr_CA").name,
            "108 - 208 - Total des CTI/RTI et des redressements",
        )
        self.assertEqual(
            report_line.with_context(lang="en_US").name,
            "108 - 208 - ITCs/ITRs and adjustments",
        )
        ret = self._return("qst", date(2026, 1, 1), date(2026, 3, 31))
        names = {
            line.code: line.name for line in ret.with_context(lang="fr_CA").line_ids
        }
        self.assertTrue(
            names["208"].startswith("Total des CTI/RTI et des redressements"),
            names["208"],
        )
        self.assertTrue(names["203"].startswith("Taxe exigible"), names["203"])
        self.assertEqual(names["101"], "Total des fournitures (chiffre d'affaires)")
        # The form numbers still come from the English name.
        self.assertIn("203", names)

    def test_drill_down(self):
        ret = self._return("gst_hst", date(2026, 1, 1), date(2026, 3, 31))
        line = ret.line_ids.filtered(lambda r: r.code == "109")
        action = line.action_open_move_lines()
        items = self.env["account.move.line"].search(action["domain"])
        # Tax lines of the three taxed sales, the credit note and the bill.
        self.assertEqual(len(items), 4)
        self.assertTrue(all(item.tax_line_id for item in items))

    def test_overlap_and_default_period(self):
        self._return("gst_hst", date(2026, 1, 1), date(2026, 3, 31))
        with self.assertRaises(ValidationError):
            self._return("gst_hst", date(2026, 3, 1), date(2026, 5, 31))
        self.company.l10n_ca_gst_filing_frequency = "quarterly"
        bounds = self.env["l10n.ca.tax.return"]._l10n_ca_period_bounds(
            self.company, "quarterly", date(2026, 10, 26)
        )
        self.assertEqual(bounds, (date(2026, 10, 1), date(2026, 12, 31)))
