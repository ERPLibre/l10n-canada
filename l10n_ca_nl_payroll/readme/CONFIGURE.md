Payroll > Configuration > Provincial Payroll Accounts, a record for
Newfoundland and Labrador:

- *Employer Tax Account Number*: the Health and Post-Secondary Education
  Tax account of the company.
- *Associated Employer* and *Exemption Allocated to the Company*: for a
  member of a group of associated employers (Income Tax Act s. 256, as
  extended by the Revenue Administration Act s. 2.01), the share of the
  2,000,000 exemption that the allocation agreement filed with the
  Department of Finance gives the company. Enter 0 when the group filed
  no agreement: the group then has no exemption.
- *Eligible for the Exemption*: leave checked; the statute gives the
  exemption to every employer.
- *Rate Basis* and the total remuneration: not used in Newfoundland and
  Labrador, whose tax has one rate and an exemption that does not depend
  on the size of the employer. The payslip does not warn when they are
  left at 0.
- *Workers' Compensation Account Number* and *Rate per $100*: the
  WorkplaceNL firm number and the assessment rate of the industry class
  notified for the year (leave 0 without an account).

Installing the module adds the Newfoundland and Labrador rules to the
*Canada - Base* structure of every company and, with the `ca_2023` chart,
proposes the accounts of the tax and of the assessment (expense 512121,
payable 221206).

On each contract whose province of employment is Newfoundland and
Labrador, page *Canadian Payroll*, group *Provincial TD1*: the TD1NL
claim (basic personal amount, total claim amount, or exempt for claim
code E), the other provincial credits authorized by a tax services office
and the additional tax per pay; *Not Covered by Workers' Compensation*
for a proprietor or partner of an unincorporated business without
optional personal coverage.

## Basic personal amount of July 2026

A contract that claims the basic personal amount follows the dated
parameter: 11,188 for the pays dated before July 1, 2026 and 15,000 from
July 1. A contract with a *total claim amount* entered from a TD1NL keeps
that amount: the CRA does not require a new TD1NL from an employee who
filed one before July 1 with the lower amount, and the employer raises
the amount of the contract by 3,812 (15,000 - 11,188) for the pays from
July.

## Parameters and their sources

| Code | 2026 | 2027 | Use | Source |
|---|---|---|---|---|
| `l10n_ca.nl.brackets` | 8.7% / 14.5% from 44,678 / 15.8% from 89,354 / 17.8% from 159,528 / 19.8% from 223,340 / 20.8% from 285,319 / 21.3% from 570,638 / 21.8% from 1,141,275 | | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1 |
| `l10n_ca.nl.bpa` | 11,188 from January 1; 15,000 from July 1 | | TCP without a TD1NL | T4127 122nd and 123rd editions, table 8.2; TD1NL 2026; Bill 16 (Income Tax Act, 2000) |
| `l10n_ca.nl.employer_tax.rates` | 2% | | Rate of the Health and Post-Secondary Education Tax | Revenue Administration Act, s. 73(1); Department of Finance |
| `l10n_ca.nl.employer_tax.exemption` | 2,000,000 | | Remuneration of the year exempt from the tax | Revenue Administration Act, s. 2(w) and 2(qqq); Department of Finance |
| `l10n_ca.nl.wcb.max_insurable` | 80,935 | 82,800 | Assessable earnings of the year | WorkplaceNL, Annual Assessment and news releases |

The tax rate and the exemption are in the statute without a yearly
figure: their 2026 versions stay in force until an amending act changes
them. The 2027 basic personal amount (15,000 indexed by the consumer
price index) is not yet published: a pay of 2027 warns that it uses the
2026 amounts until a version is entered.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.087 x TCP;
  K2P = 0.087 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.087 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract. T2 = T4.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- Health and Post-Secondary Education Tax of a pay = 2% x (max(0, R + G -
  E) - max(0, R - E)), G the gross of the pay, R the Newfoundland and
  Labrador remuneration paid by the company earlier in the year, E the
  exemption (2,000,000, or the allocated share of an associated
  employer). This is the cumulative computation of the monthly return:
  the allocated deduction is reduced by the payroll of each period until
  it is exhausted.
- WorkplaceNL: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); assessment = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month in March: A = 59,434.99; T4 = 0.145 x 59,434.99 - 2,591
  - 973.36 - 328.41 = 4,725.31; (5,338.28 + 4,725.31) / 12 = 838.63, of
  which 444.86 federal and 393.77 provincial. In July (TCP 15,000): T4 =
  4,393.67, 811.00 of which 366.14 provincial.
- T4032 for Newfoundland and Labrador, 1,300 a week with an RRSP of 80:
  213.99 (the CRA's total) in January, 114.57 federal and 99.42
  provincial; 207.61 from July, 93.04 provincial. 1,600 a week above the
  YMPE: 327.30 in January, 180.89 federal and 146.41 provincial; 320.92
  from July, 140.03 provincial.
- Health and Post-Secondary Education Tax with an allocated exemption of
  12,000 and 5,000 a month: nothing in January and February, 2% x 3,000 =
  60.00 in March, 2% x 5,000 = 100.00 from April. An employer not
  associated paying 900,000 a month: nothing until 2,000,000, 14,000.00
  in March, 18,000.00 from April.

## Not covered

- Registered charities and the non-profit organizations recognized by the
  Department of Finance treat each establishment as a separate employer
  with its own exemption; the payslips apply one exemption per company
  and province, so such an employer accrues more tax than its returns
  declare.
- Remuneration of employees who report for work outside the province, or
  partly in it, is counted by the province of employment of the contract.
- The WorkplaceNL minimum annual assessment (50), the PRIME refunds and
  charges, the construction industry levy and the optional personal
  coverage are on the assessment notice, not in the payslips.
