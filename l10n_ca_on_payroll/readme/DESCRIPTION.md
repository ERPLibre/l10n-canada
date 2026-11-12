Ontario payroll on top of the Canadian federal payroll (`l10n_ca_payroll`),
for employees whose province of employment is Ontario.

- Ontario income tax per the CRA *Payroll Deductions Formulas* (T4127),
  option 1: basic Ontario tax T4 on the annual taxable income A of the
  federal computation (so the RPP and RRSP contributions, union dues and
  support payments that lower A also lower the Ontario tax), Ontario
  constants KP derived from the brackets, personal credit K1P on the TD1ON
  claim (basic personal amount by default), credit K2P for the base CPP
  contributions and the EI premiums, other credits K3P, surtax V1, Ontario
  Health Premium V2, tax reduction S with the dependants of the employee,
  additional tax per pay. An employee exempt from tax (claim code E) still
  bears the Ontario Health Premium. Bonuses, retroactive pay and other
  non-periodic payments are taxed with the bonus formulas of T4127 (the
  Ontario tax of the year with the payment less the tax without it).
- Employer Health Tax: the rate of the annual total Ontario remuneration of
  the company applied to the remuneration of each pay above the exemption
  left in the year, with the exemption of an eligible employer, of a
  registered charity or the share allocated to an associated employer.
- WSIB premium at the rate per $100 of the company, on the insurable
  earnings of each worker up to the annual maximum.
- Every rate, ceiling, bracket table and credit amount is a dated time
  parameter (`l10n_ca.on.*`) shipped for 2025 and 2026, and 2027 where it
  is published; the official sources are listed in Payroll > Configuration
  > Canadian Official Sources and in `static/description/sources.html`.

The Ontario income tax is remitted to the CRA with the federal deductions
(PD7A) and reported in box 22 of the T4 by the federal module.
