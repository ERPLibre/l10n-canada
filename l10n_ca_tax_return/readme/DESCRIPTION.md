Computes, closes and prints the Canadian sales tax returns from the tax report
definitions of `l10n_ca`, which Odoo Community ships without a viewer.

- **GST/HST return (GST34)**: lines 90 to 115 of the CRA return, as entered in
  GST/HST NETFILE.
- **Quebec return (FPZ-500)**: lines 101 to 116 (GST/HST) and 203 to 216
  (QST) of the return filed with Revenu Québec.

A generic engine evaluates the `account.report` of the return: `tax_tags`
expressions on the posted, exigible journal items of the period with the sign
conventions of the tax reports (`tax_negate`, `tax_tag_invert`), then the
aggregation formulas and their bounds. Every line opens the journal items it
sums.

- **Line 101 completeness**: line 101 of both returns is the total revenue of
  the period, zero-rated exports and exempt supplies included. The module adds
  the FPZ-500 line 101 grid to the `0% Int` and `0% Exempt` sales taxes of the
  `ca_2023` chart: through the chart template for new companies, and through
  the installation hook for existing companies and their open-period journal
  items. Line 101 is informational and does not change the net tax.
- **Quick method**: remittance = tax-included eligible supplies × remittance
  rate (GST/HST by tax rate, QST by activity), 1% credit on the first eligible
  supplies of each fiscal year, input tax credits limited to capital property.
  Sales booked on a capital property account (fixed or non-current asset) are
  not eligible supplies: their tax is remitted in full on lines 103 and 203.
  On the FPZ-500, line 101 includes the GST/HST charged, not the QST. The
  closing entry posts the difference with the tax recorded in the books to a
  gain account.
- **Bad debts**: a wizard on a posted customer invoice writes off the unpaid
  balance and deducts the GST/HST and QST it contains (lines 107 and 207), or
  records the recovery of a written-off debt (lines 104 and 204), following
  Excise Tax Act s. 231.
- **Closing entry**: moves the period balances of the tax accounts to the
  account of the tax authority (CRA or Revenu Québec).
- **Filing**: filing date and confirmation number, PDF laid out by form line
  and XLSX export (`report_xlsx`).

Rates, thresholds, credits and due date offsets are dated parameters of
`l10n_ca_time_parameter` (codes `l10n_ca.gst_quick.*`, `l10n_ca.qst_quick.*`,
`l10n_ca.sales_tax.*`).
