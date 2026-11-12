Alberta payroll on top of the Canadian federal payroll (`l10n_ca_payroll`),
for employees whose province of employment is Alberta, on the common
provincial engine of the federal module.

- Alberta income tax per the CRA *Payroll Deductions Formulas* (T4127),
  option 1: basic tax T4 on the annual taxable income A of the federal
  computation (first bracket of 8% since 2025), constants KP derived from
  the brackets, personal credit K1P on the TD1AB claim (basic personal
  amount by default), credit K2P for the base CPP contributions and the EI
  premiums, other credits K3P, the Alberta supplemental tax credit K5P,
  additional tax per pay; the tax on bonuses (TB). The federal and
  provincial tax of the pay is rounded once, as T4127 does. Checked
  against the step-by-step examples of the T4032 for Alberta (January
  2026).
- WCB-Alberta premiums: the rate per $100 of the company on the
  assessable earnings of each worker up to the maximum assessable
  earnings of the year.
- Alberta has no employer payroll tax and no labour-sponsored funds tax
  credit.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WCB-Alberta fact sheet that states the maximum
  assessable earnings.

The Alberta parameters start on January 1, 2026.
