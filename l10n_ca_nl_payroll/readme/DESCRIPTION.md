Newfoundland and Labrador payroll on top of the Canadian federal payroll
(`l10n_ca_payroll`), for employees whose province of employment is
Newfoundland and Labrador, on the common provincial engine of the federal
module.

- Newfoundland and Labrador income tax per the CRA *Payroll Deductions
  Formulas* (T4127), option 1: basic tax T4 on the annual taxable income A
  of the federal computation over eight brackets, constants KP derived
  from the brackets, personal credit K1P on the TD1NL claim (basic
  personal amount by default), credit K2P for the base CPP contributions
  and the EI premiums, other credits K3P, additional tax per pay; the tax
  on bonuses (TB). The federal and provincial tax of the pay is rounded
  once, as T4127 does. The basic personal amount is 11,188 for the pays
  of January to June 2026 and the prorated 15,000 from the first pay of
  July 2026 (T4127 123rd edition). Checked against the step-by-step
  examples of the T4032 for Newfoundland and Labrador of January and of
  July 2026.
- Health and Post-Secondary Education Tax (payroll tax): 2% of the
  remuneration of the year above the exemption of 2,000,000, the
  exemption being consumed by the first pays of the year; associated
  employers take the share of their allocation agreement.
- WorkplaceNL assessments: the rate per $100 of the company on the
  assessable earnings of each worker up to the maximum of the year.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WorkplaceNL page that gives the maximum
  assessable earnings by year.

The Newfoundland and Labrador parameters start on January 1, 2026.
