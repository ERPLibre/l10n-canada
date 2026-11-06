Owner-manager corporate tax follow-up for a Quebec Canadian-controlled
private corporation (CCPC). Every rate, threshold and deadline offset is a
dated parameter of `l10n_ca_time_parameter`.

- **Shareholder loans** (ITA s. 15(2), 15(2.6), 80.4): accounts and partners
  are flagged; per shareholder and fiscal year, the module follows the
  balance, the loans made in the year (first-in first-out), the repayment
  deadline (one year after the year end), the amount that becomes taxable
  when the deadline passes, and the deemed interest at the CRA prescribed
  rate, quarter by quarter. A scheduled action creates a to-do activity
  before the deadline.
- **Quebec small business deduction, remunerated hours rule**: hours per
  fiscal year (employees, majority shareholder at 1.1 times all the hours
  worked, weekly cap), brought to a full year when the fiscal year is
  shorter, hours of the associated corporations for the preceding-year
  test, primary and manufacturing sectors criterion; the factor is linear
  between 5,000 and 5,500 hours. `res.company._l10n_ca_get_paid_hours()` is the hook a
  payroll bridge extends.
- **Corporate income tax estimate**: accounting income from the books,
  adjustments (meals and entertainment, book depreciation, capital cost
  allowance through the `_l10n_ca_get_cca_adjustments()` hook, other),
  income split between active business, investment and personal services
  business income, business limit with its taxable capital and passive
  income grinds, federal tax (abatement, general rate reduction, small
  business deduction, refundable tax), Quebec tax with the remunerated
  hours factor and its own business limit (prorated for a short year,
  ground on paid-up capital), instalment schedule and balance-due dates. It is clearly
  labelled as an estimate.
- **Dividends**: declaration and payment entries, GRIP check on eligible
  dividends, T5 and RL-3 slip data per recipient and calendar year, summary
  totals, CSV and XLSX export of the boxes for the CRA web forms and the
  Revenu Quebec online service.
