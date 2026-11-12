Payroll > Configuration > Provincial Payroll Accounts, a record for
British Columbia:

- Employer Health Tax: the account number, the *Rate Basis* (total British
  Columbia remuneration of the previous year, or an estimate of the year)
  and its amount, which selects the rate and the exemption. A registered
  charitable or non-profit employer ticks *Registered Charity* and gets the
  charity amounts. Associated employers tick *Associated Employer*, enter
  the remuneration of the whole group as the basis and the share of the
  1,000,000 exemption that the allocation agreement gives the company (0
  when the group exceeds 1,500,000). An employer that the Act excludes
  from the exemption unticks *Eligible for the Exemption*.
- WorkSafeBC: the account number and the premium rate per $100 of the
  rate notice of the year (leave 0 without an account).

Installing the module adds the British Columbia rules to the *Canada -
Base* structure of every company and, with the `ca_2023` chart, proposes
the accounts of the employer contributions (expense 512121, payable
221206).

On each contract whose province of employment is British Columbia, page
*Canadian Payroll*, group *Provincial TD1*: the TD1BC claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other British Columbia credits authorized by a tax services office and the
additional tax per pay; *Not Covered by Workers' Compensation* for a
proprietor or partner without optional personal coverage.

## Parameters and their sources

| Code | January 2026 | July 1, 2026 | 2027 | Use | Source |
|---|---|---|---|---|---|
| `l10n_ca.bc.brackets` | 5.06% / 7.70% from 50,363 / 10.50% from 100,728 / 12.29% from 115,648 / 14.70% from 140,430 / 16.80% from 190,405 / 20.50% from 265,545 | first rate 6.14% (5.60% prorated) | first rate 5.60%, thresholds of 2026 | V, KP, rate of K1P and K2P | T4127 122nd and 123rd editions, table 8.1 and "Upcoming changes for January 1, 2027"; BC tax rates page |
| `l10n_ca.bc.bpa` | 13,216 | | 13,216 (indexation paused) | TCP without a TD1BC | T4127 table 8.2, TD1BC 2026, BC basic tax credits page |
| `l10n_ca.bc.tax_reduction_basic` | 575 | 805 (690 prorated) | 690 | S2 of factor S | T4127 step 5, British Columbia; BC basic tax credits page |
| `l10n_ca.bc.tax_reduction_threshold` | 25,570 | | (indexation paused) | Factor S | T4127 step 5 |
| `l10n_ca.bc.tax_reduction_rate` | 3.56% | | | Factor S | T4127 step 5 |
| `l10n_ca.bc.tax_reduction_max_income` | 41,722 | 44,952 | (indexation paused) | Factor S | T4127 step 5 |
| `l10n_ca.bc.employer_tax.rates` | 5.85% up to 1,500,000, 1.95% above | | | Employer Health Tax | Employer Health Tax Act, ss. 8, 10, 11 |
| `l10n_ca.bc.employer_tax.exemption`, `.exemption_threshold` | 1,000,000; 1,500,000 | | | Employer Health Tax | Same |
| `l10n_ca.bc.employer_tax.charity_rates` | 2.925% up to 4,500,000, 1.95% above | | | Charities | Same, ss. 20, 21, 29 |
| `l10n_ca.bc.employer_tax.charity_exemption`, `.charity_exemption_threshold` | 1,500,000; 4,500,000 | | | Charities | Same |
| `l10n_ca.bc.wcb.max_insurable` | 127,500 | | 130,800 | Assessable earnings of the year | WorkSafeBC maximum wage rates |

A blank cell keeps the previous version. A 2027 figure that the official
texts do not give is not shipped.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = lowest rate x TCP;
  K2P = lowest rate x (P x C x 0.0495 / 0.0595, at most the base CPP
  maximum x PM / 12) + lowest rate x (P x EI, at most the EI maximum);
  K3P = the other credits of the contract.
- S = min(T4, S2) when A <= 25,570; min(T4, S2 - (A - 25,570) x 3.56%)
  when A <= the maximum income (41,722 from January 2026, 44,952 from
  July 2026); 0 above; at least 0. From July 2026 the prorated S2 of 805
  is still cut at 44,952, the maximum of the annual 690.
- T2 = T4 - S, at least 0.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- Employer Health Tax of a pay = rate x (max(0, R + G - E) - max(0, R -
  E)), R the British Columbia remuneration paid before it in the year, G
  the gross of the pay, E the exemption, the rate and E those of the rate
  basis: total up to 1,000,000, no tax; up to 1,500,000, 5.85% of the
  excess over 1,000,000; above, 1.95% of the whole remuneration (E = 0).
- WorkSafeBC: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); premium = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month, January 2026: A = 59,435.04; T4 = 0.077 x 59,435.04 -
  1,330 - 668.73 - 191.00 = 2,386.76, no reduction; (5,338.29 + 2,386.76)
  / 12 = 643.75, of which 444.86 federal and 198.89 British Columbia. Paid
  in July: T4 = 0.077 x 59,435.04 - 786 - 811.46 - 231.77 = 2,747.26;
  (5,338.29 + 2,747.26) / 12 = 673.80, 228.94 British Columbia.
- T4032 for British Columbia, 1,300 a week with an RRSP of 80: 164.97 in
  January (the CRA's total), 114.57 federal and 50.40 British Columbia;
  171.80 from July, 57.23 British Columbia. 1,600 a week above the YMPE:
  256.21 in January, 180.89 federal and 75.32 British Columbia; 262.96
  from July, 82.07 British Columbia.
- 2,000 a month: A = 23,795.04, T4 = 464.16, S = 464.16, no British
  Columbia tax. 3,000 a month: A = 35,675.04, T4 = 1,025.33, S = 575 -
  10,105.04 x 3.56% = 215.26, T2 = 810.07 (July: 1,244.18 - 445.26 =
  798.92).
- Employer Health Tax, total remuneration 1,200,000: 5.85% x 200,000 =
  11,700 on the pay that crosses 1,000,000; 1,800,000: 1.95% of every pay;
  a charity paying 2,500,000: 2.925% x 1,000,000 = 29,250.

## Not covered

- The Employer Health Tax is accrued pay by pay at the rate of the rate
  basis; the annual return sets it on the actual remuneration. A company
  whose actual remuneration ends in another band than its basis gets its
  difference on the return.
- Charitable or non-profit employers: the Act applies the exemption and
  the notch to each qualifying location and allocates the remuneration of
  the other locations; the payslip applies them to the whole British
  Columbia remuneration of the company. A charity that is also an
  associated employer is computed as an associated employer.
- The proration of the exemption and of the notch for a part-year
  permanent establishment.
- The WorkSafeBC classification rate, experience rating and personal
  coverage of proprietors are on the rate notice, not in the payslips; no
  minimum premium is applied.
