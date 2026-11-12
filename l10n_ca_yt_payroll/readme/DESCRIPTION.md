Yukon payroll on top of the Canadian federal payroll (`l10n_ca_payroll`),
for employees whose province or territory of employment is Yukon, on the
common provincial engine of the federal module.

- Yukon income tax per the CRA *Payroll Deductions Formulas* (T4127),
  option 1: basic tax T4 on the annual taxable income A of the federal
  computation (after the prescribed zone deduction HD), constants KP
  derived from the five brackets, personal credit K1P on the TD1YT claim,
  credit K2P for the base CPP contributions and the EI premiums, other
  credits K3P, the territorial Canada employment credit K4P, additional
  tax per pay; the tax on bonuses (TB). The federal and territorial tax
  of the pay is rounded once, as T4127 does. Checked against the
  step-by-step examples of the T4032 for Yukon (January 2026).
- Basic personal amount BPAYT: without a TD1YT, the federal basic
  personal amount of the net income, reduced from 16,452 to 14,829
  between 181,440 and 258,482 (2026), as T4127 asks.
- Workers' Safety and Compensation Board (WSCB) assessment premiums: the
  rate per $100 of the rate group of the company on the assessable
  earnings of each worker up to the maximum annual earnings.
- Yukon has no employer payroll tax and no labour-sponsored funds credit.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WSCB page that states the maximum annual
  earnings.

The Yukon parameters start on January 1, 2026.
