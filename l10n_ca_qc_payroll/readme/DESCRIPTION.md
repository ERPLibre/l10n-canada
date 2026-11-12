Quebec payroll on top of the Canadian federal payroll (`l10n_ca_payroll`),
for employees whose province of employment is Quebec.

- Quebec Pension Plan instead of the CPP: base and first additional
  contribution, second additional contribution (QPP2) between the maximum
  and the additional maximum pensionable earnings, contributions until
  December 31 of the year the employee turns 72. EI at the Quebec reduced
  rate and the federal abatement come from the federal module.
- Quebec Parental Insurance Plan: employee and employer premiums up to the
  maximum insurable earnings; the employee premium enters the federal K2
  credit.
- Quebec income tax per the Revenu Québec *Formulas to Calculate Source
  Deductions and Contributions* (TP-1015.F) for regular payments: annual
  taxable income, deduction for workers, deduction of the additional QPP
  contributions, RPP, RRSP and similar contributions withheld at source
  (F), TP-1015.3 claim (basic personal amount by default),
  deductions and credits authorized on a TP-1016, additional tax per pay.
  Bonuses, retroactive payments and other similar lump-sum payments follow
  the second method of section 2.1.2: the rate of the bracket of the
  annual income that includes them, applied to the payment less its share
  of the additional QPP contributions, or 7% when the annual salary and
  the lump sums of the year are at most the basic personal amount.
- Employer contributions: Health Services Fund (rate from the total payroll
  and the sector), contribution related to labour standards (CNT), CNESST
  premium at the rate of the company, WSDRF when the total payroll exceeds
  its threshold.
- Every rate, maximum, bracket table, credit amount and due date is a dated
  time parameter (`l10n_ca.qpp.*`, `l10n_ca.qpip.*`, `l10n_ca.qc.*`) shipped
  for 2025 and 2026.
- Year-end: RL-1 slips (boxes A, B.A, B.B, C, D, E, F, G, H, I), RL-1 summary
  (RLZ-1.S lines 21 to 82, with the reconciliation of the health services
  fund, labour standards and WSDRF contributions), Revenu Québec
  remittances per period of the company frequency (TPZ-1015.R.14), T4 boxes
  55 and 56, CSV exports.
