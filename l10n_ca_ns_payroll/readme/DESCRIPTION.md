Nova Scotia payroll on top of the Canadian federal payroll
(`l10n_ca_payroll`), for employees whose province of employment is Nova
Scotia, on the common provincial engine of the federal module.

- Nova Scotia income tax per the CRA *Payroll Deductions Formulas*
  (T4127), option 1: basic tax T4 on the annual taxable income A of the
  federal computation, constants KP derived from the brackets, personal
  credit K1P on the TD1NS claim (basic personal amount by default, the
  same for every income from 2026), credit K2P for the base CPP
  contributions and the EI premiums, other credits K3P, additional tax per
  pay; the labour-sponsored funds tax credit LCP (20% of the shares
  withheld, at most 2,000 a year); the tax on bonuses (TB). The federal
  and provincial tax of the pay is rounded once, as T4127 does. Checked
  against the step-by-step examples of the T4032 for Nova Scotia (January
  2026).
- WCB Nova Scotia premiums: the rate per $100 of the company on the
  assessable earnings of each worker up to the yearly maximum.
- Nova Scotia has no employer payroll tax.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WCB Nova Scotia page that states the maximum
  assessable earnings.

The Nova Scotia parameters start on January 1, 2026.
