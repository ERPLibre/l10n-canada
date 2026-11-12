Nunavut payroll on top of the Canadian federal payroll (`l10n_ca_payroll`),
for employees whose province or territory of employment is Nunavut, on the
common provincial engine of the federal module.

- Nunavut income tax per the CRA *Payroll Deductions Formulas* (T4127),
  option 1: basic tax T4 on the annual taxable income A of the federal
  computation, constants KP derived from the brackets, personal credit K1P
  on the TD1NU claim (basic personal amount by default), credit K2P for
  the base CPP contributions and the EI premiums, other credits K3P,
  additional tax per pay; the tax on bonuses (TB). The federal and
  territorial tax of the pay is rounded once, as T4127 does. The territory
  has no surtax, tax reduction or labour-sponsored funds credit. Checked
  against the step-by-step examples of the T4032 for Nunavut (January
  2026).
- Nunavut payroll tax: 2% of the remuneration, borne by the employee and
  withheld by the employer on each pay (*Payroll Tax Act*), as the
  deduction *Nunavut Payroll Tax* payable to the Government of Nunavut. It
  is not an employer contribution and does not lower the taxable income of
  the CRA formulas.
- Workers' Safety and Compensation Commission (WSCC) assessments: the rate
  per $100 of the company on the assessable payroll of each worker up to
  the Year's Maximum Insurable Remuneration of Nunavut.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WSCC page that lists the Year's Maximum
  Insurable Remuneration.

The Nunavut parameters start on January 1, 2026.
