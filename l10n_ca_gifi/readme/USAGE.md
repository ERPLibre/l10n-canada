Invoicing (Accounting) > Reporting > Canada > GIFI Statements: create a
statement, choose the fiscal year (the last one closed is proposed) and
click **Compute**.

- Tab *Checks*: correct every error (unmapped account, unbalanced balance
  sheet) and review the warnings, then compute again.
- Tabs *Schedule 100*, *Schedule 101* (first year only) and *Schedule 125*:
  the amounts to report, in whole dollars. Assets, liabilities, equity,
  revenue and expenses are positive; contra accounts (allowances,
  accumulated amortization) are negative; closing inventory (8500),
  dividends (3700) and income taxes (9990, 9995) are positive and
  subtracted by their total.
- **CSV Schedule 100 / 101 / 125**: one `code,amount` line per item, for
  the GIFI import of the tax software. **XLSX** and **PDF** print the
  whole statement.

Rounding: each item is rounded to the dollar and the totals add the
rounded items. A difference of rounding on the balance sheet is absorbed
by 3600, and between 3849 and 3600 by 3740; both are listed in the checks.
