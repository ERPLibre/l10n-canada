Prince Edward Island payroll on top of the Canadian federal payroll
(`l10n_ca_payroll`), for employees whose province of employment is Prince
Edward Island, on the common provincial engine of the federal module.

- Prince Edward Island income tax per the CRA *Payroll Deductions
  Formulas* (T4127), option 1: basic tax T4 on the annual taxable income A
  of the federal computation, constants KP derived from the brackets,
  personal credit K1P on the TD1PE claim (basic personal amount of 15,000
  by default), credit K2P for the base CPP contributions and the EI
  premiums, other credits K3P, additional tax per pay; the tax on bonuses
  (TB). The federal and provincial tax of the pay is rounded once, as
  T4127 does. The bracket of 20% above 200,000 enacted for 2026 is
  withheld at the prorated rate of 21% from July 1, 2026, then at 20%
  from January 1, 2027. Checked against the step-by-step examples of the
  T4032 for Prince Edward Island (January and July 2026).
- WCB PEI assessments: the rate per $100 of the company on the assessable
  earnings of each worker up to the maximum assessable earnings of the
  year.
- Prince Edward Island has no employer payroll tax, no surtax and no
  labour-sponsored funds tax credit in the source deductions.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WCB PEI page that states the maximum assessable
  earnings.

The Prince Edward Island parameters start on January 1, 2026.
