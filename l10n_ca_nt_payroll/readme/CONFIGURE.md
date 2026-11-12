Payroll > Configuration > Provincial Payroll Accounts, a record for the
Northwest Territories: the WSCC account number and the assessment rate per
$100 of the industry subclass of the year (leave 0 without an account).

Installing the module adds the Northwest Territories rules to the *Canada -
Base* structure of every company and, with the `ca_2023` chart, proposes
the accounts of the payroll tax (221206 debited, 221203 credited, like the
federal source deductions) and of the WSCC assessment (expense 512121,
payable 221206).

On each contract whose province of employment is the Northwest
Territories, page *Canadian Payroll*: in group *Provincial TD1* the TD1NT
claim (basic personal amount, total claim amount, or exempt for claim code
E), the other territorial credits authorized by a tax services office and
the additional tax per pay; in group *Employment*, *Not Covered by Workers'
Compensation* for a director, a business owner or a self-employed person
without Personal Optional Coverage, and *Exempt from the Northwest
Territories Payroll Tax* for an employee whose remuneration is not subject
(see below).

*Prescribed Zone Deduction (Annual)* of the federal module carries the
deduction for living in a prescribed zone that the employee claims on the
TD1 (HD of T4127; the Northwest Territories lie in the prescribed northern zone): it lowers
the annual taxable income A of the federal and territorial tax.

## Parameters and their sources

| Code | 2026 | Use | Source |
|---|---|---|---|
| `l10n_ca.nt.brackets` | 5.9% / 8.6% from 53,003 / 12.2% from 106,009 / 14.05% from 172,346 | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1 |
| `l10n_ca.nt.bpa` | 18,198 | TCP without a TD1NT | T4127 table 8.2, TD1NT 2026 |
| `l10n_ca.nt.payroll_tax.rate` | 2% | Payroll tax of the employee | *Payroll Tax Act*, s. 3(1) |
| `l10n_ca.nt.wcb.max_insurable` | 116,000 | Assessable payroll of the year | WSCC Employer Rates; R-080-2010, s. 1 |

No figure changed on July 1, 2026; the 2027 figures are not published.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.059 x TCP;
  K2P = 0.059 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.059 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract. T2 = T4.
- Tax of the pay: (T1 + T2) / P rounded once; the territorial line is that
  total less the federal line, plus the additional tax of the contract.
- Payroll tax of the pay = 0.02 x the gross of the pay, rounded to the
  cent; 0 for an exempt contract. A credit note bears the amount of the
  pay it takes back and counts negatively.
- WSCC: assessable payroll of the pay = min(gross, maximum - assessable
  payroll of the year so far); assessment = rate x assessable payroll /
  100.

## Worked examples (tests)

- 5,000 a month: A = 59,435.04; T4 = 0.086 x 59,435.04 - 1,431 - 1,073.68
  - 222.71 = 2,384.02; (5,338.29 + 2,384.02) / 12 = 643.53, of which
  444.86 federal and 198.67 Northwest Territories; payroll tax 100.00.
- T4032 for the Northwest Territories, 1,600 a week above the YMPE:
  259.55 (the CRA's total), 180.89 federal and 78.66 Northwest
  Territories; payroll tax 32.00.
- T4032, 1,300 a week with an RRSP of 80 and an annual deduction for
  living in a prescribed zone of 4,015 (*Prescribed Zone Deduction* of
  the contract): 142.95 (the CRA's total), 98.75 federal and 44.20
  Northwest Territories.

## Not covered

- Payroll tax: the module applies the rate to the gross of each pay.
  Not modelled: the pro-ration by the days worked in the territory of an
  employee who normally works outside it, and the 5,000 threshold below
  which such an employee owes nothing (Act s. 3(2) to (2.2); Regulations
  s. 2) — mark the contract exempt when the remuneration of the year is
  not expected to exceed it; the exclusion of the amounts deductible under
  s. 8(1)(c) of the Income Tax Act (clergy residence); taxable benefits
  and employer RRSP contributions that are not part of the gross of the
  payslip; the annual reconciliation and the refund of an over-collection
  (annual return).
- The WSCC minimum assessment (200), the subclass rates and the Personal
  Optional Coverage of directors and owners are on the assessment, not in
  the payslips.
