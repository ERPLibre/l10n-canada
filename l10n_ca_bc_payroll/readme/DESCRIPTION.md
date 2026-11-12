British Columbia payroll on top of the Canadian federal payroll
(`l10n_ca_payroll`), for employees whose province of employment is British
Columbia, on the common provincial engine of the federal module.

- British Columbia income tax per the CRA *Payroll Deductions Formulas*
  (T4127), option 1: basic tax T4 on the annual taxable income A of the
  federal computation, constants KP derived from the brackets, personal
  credit K1P on the TD1BC claim (basic personal amount by default),
  credit K2P for the base CPP contributions and the EI premiums, other
  credits K3P, the BC tax reduction (factor S), additional tax per pay;
  the tax on bonuses (TB). The federal and provincial tax of the pay is
  rounded once, as T4127 does. The rates and the reduction prorated from
  July 1, 2026 (lowest rate 6.14%, basic reduction 805) and the 2027
  amounts (lowest rate 5.60%, basic reduction 690, indexation paused) are
  dated parameters. Checked against the step-by-step examples of the
  T4032 for British Columbia of January and July 2026.
- Employer Health Tax: no tax up to the exemption of 1,000,000, 5.85% of
  the remuneration above it up to a total remuneration of 1,500,000, 1.95%
  of the whole remuneration above; the amounts of a charitable or
  non-profit employer (1,500,000, 2.925% up to 4,500,000); the exemption
  shared by associated employers.
- WorkSafeBC premiums: the rate per $100 of the company on the assessable
  earnings of each worker up to the maximum wage rate of the year.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WorkSafeBC page of the maximum wage rates.

The British Columbia parameters start on January 1, 2026.
