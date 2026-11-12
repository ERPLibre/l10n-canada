Manitoba payroll on top of the Canadian federal payroll
(`l10n_ca_payroll`), for employees whose province of employment is
Manitoba, on the common provincial engine of the federal module.

- Manitoba income tax per the CRA *Payroll Deductions Formulas* (T4127),
  option 1: basic tax T4 on the annual taxable income A of the federal
  computation, constants KP derived from the brackets, personal credit
  K1P on the TD1MB claim, credit K2P for the base CPP contributions and
  the EI premiums, other credits K3P, additional tax per pay; the
  income-tested basic personal amount BPAMB (15,780 up to an annual
  income of 200,000, reduced linearly to 0 at 400,000) when the employee
  files no TD1MB; the labour-sponsored funds tax credit LCP (15% of the
  shares withheld, at most 1,800 a year); the tax on bonuses (TB). The
  federal and provincial tax of the pay is rounded once, as T4127 does.
  Checked against the step-by-step examples of the T4032 for Manitoba
  (January 2026).
- Health and Post Secondary Education Tax Levy: no levy up to a total
  Manitoba remuneration of 2,500,000, 4.3% of the remuneration above it
  up to 5,000,000 (notch provision), 2.15% of the whole remuneration
  above 5,000,000, accrued on each pay once the exemption is used up.
- WCB Manitoba premiums: the rate per $100 of the company on the
  assessable earnings of each worker up to the yearly maximum.
- The official sources of these figures, in Payroll > Configuration >
  Canadian Official Sources and in `static/description/sources.html`, and
  a weekly reading of the WCB Manitoba fact sheet that states the maximum
  assessable earnings.

The Manitoba parameters start on January 1, 2026.
