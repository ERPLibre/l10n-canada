New Brunswick payroll on top of the Canadian federal payroll
(`l10n_ca_payroll`), for employees whose province of employment is New
Brunswick, on the common provincial engine of the federal module.

- New Brunswick income tax per the CRA *Payroll Deductions Formulas*
  (T4127), option 1: basic tax T4 on the annual taxable income A of the
  federal computation, constants KP derived from the brackets, personal
  credit K1P on the TD1NB claim (basic personal amount by default),
  credit K2P for the base CPP contributions and the EI premiums, other
  credits K3P, additional tax per pay; the labour-sponsored funds tax
  credit LCP (20% of the shares withheld, at most 2,000 a year); the tax
  on bonuses (TB). The federal and provincial tax of the pay is rounded
  once, as T4127 does. Checked against the step-by-step examples of the
  T4032 for New Brunswick (January 2026).
- WorkSafeNB assessments: the rate per $100 of the company on the
  assessable earnings of each worker up to the yearly maximum.
- New Brunswick has no employer payroll tax.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WorkSafeNB policy that states the maximum
  assessable earnings.

The New Brunswick parameters start on January 1, 2026.
