Bridge between *Canada - Owner-Manager Corporate Tax* and *Canada - Quebec
Payroll*, installed automatically when both are.

The Quebec small business deduction depends on the remunerated hours of the
corporation's employees (5,000 to 5,500 hours, thresholds in the Canadian
Time Parameters). With this module, the hours of the **done payslips** of
the fiscal year are added to the hours typed on the *Quebec Remunerated
Hours* record, through the `res.company._l10n_ca_get_paid_hours()` hook of
the corporate tax module. The record shows them as *Hours from Payroll*.

How a payslip counts:

- **Paid hours**: the hours of the `WORK100` worked days line (the full
  schedule of the contract, paid leaves included), less the hours of the
  leave lines whose leave type is *unpaid*, recognized by the code of its
  work entry type.
- **Weekly maximum**: the same parameter as the manual lines,
  `l10n_ca.qc_sbd.weekly_hours_cap` (40 hours), times the weeks of the
  payslip period; then, per employee, times the weeks covered by all the
  employee's payslips of the year, so a second payslip of the same period
  adds nothing beyond the maximum.
- **Fiscal year**: a payslip whose period straddles the year end is
  prorated by its days in each year.
- **Excluded**: payslips that are not done, refunded payslips and their
  refunds.

Every employee counts, a shareholder on the payroll included. A person
holding, directly or indirectly, the majority of the voting shares counts
1.1 times the hours worked to take an active part in the business, paid or
not (`l10n_ca.qc_sbd.shareholder_hours_factor`). Check *Majority Voting
Shareholder* on that employee (Employees > Settings tab): the hours of the
payslips then count with the factor. Type only the hours worked without pay
on a manual *Majority shareholder* line, never hours already paid through
payroll, or they are counted twice.
