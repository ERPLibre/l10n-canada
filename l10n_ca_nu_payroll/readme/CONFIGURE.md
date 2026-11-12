Payroll > Configuration > Provincial Payroll Accounts, a record for
Nunavut: the WSCC account number and the assessment rate per $100 of the
industry subclass of the year (leave 0 without an account).

Installing the module adds the Nunavut rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the payroll tax (221206 debited, 221203 credited, like the
federal source deductions) and of the WSCC assessment (expense 512121,
payable 221206).

On each contract whose province of employment is Nunavut, page *Canadian
Payroll*: in group *Provincial TD1* the TD1NU claim (basic personal
amount, total claim amount, or exempt for claim code E), the other
territorial credits authorized by a tax services office and the additional
tax per pay; in group *Employment*, *Not Covered by Workers' Compensation*
for a director, a business owner or a self-employed person without
Personal Optional Coverage, and *Exempt from the Nunavut Payroll Tax* for
an employee whose remuneration is not subject (see below).

*Prescribed Zone Deduction (Annual)* of the federal module carries the
deduction for living in a prescribed zone that the employee claims on the
TD1 (HD of T4127; Nunavut lies in the prescribed northern zone): it lowers
the annual taxable income A of the federal and territorial tax.

## Parameters and their sources

| Code | 2026 | Use | Source |
|---|---|---|---|
| `l10n_ca.nu.brackets` | 4% / 7% from 55,801 / 9% from 111,602 / 11.5% from 181,439 | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1 |
| `l10n_ca.nu.bpa` | 19,659 | TCP without a TD1NU | T4127 table 8.2, TD1NU 2026 |
| `l10n_ca.nu.payroll_tax.rate` | 2% | Payroll tax of the employee | *Payroll Tax Act*, s. 3(1); Government of Nunavut registration form (2022) and guide (2011) |
| `l10n_ca.nu.wcb.max_insurable` | 117,300 | Assessable payroll of the year | WSCC Employer Rates |

No figure changed on July 1, 2026; the 2027 figures are not published.
The Nunavut legislation site and the Department of Finance pages refuse
automated readers: their sources are marked *To verify*.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.04 x TCP;
  K2P = 0.04 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.04 x (P x EI, at most the EI maximum); K3P = the other
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

- 5,000 a month: A = 59,435.04; T4 = 0.07 x 59,435.04 - 1,674 - 786.36 -
  150.99 = 1,549.10; (5,338.29 + 1,549.10) / 12 = 573.95, of which 444.86
  federal and 129.09 Nunavut; payroll tax 100.00.
- T4032 for Nunavut, 1,600 a week above the YMPE: 237.53 (the CRA's
  total), 180.89 federal and 56.64 Nunavut; payroll tax 32.00.
- T4032, 1,300 a week with an RRSP of 80 and an annual deduction for
  living in a prescribed zone of 4,015 (*Prescribed Zone Deduction* of
  the contract): 127.27 (the CRA's total), 98.75 federal and 28.52 Nunavut.

## Not covered

- Payroll tax: the module applies the rate to the gross of each pay.
  Not modelled: the pro-ration by the days worked in Nunavut of an
  employee who normally works outside it, and the 5,000 threshold below
  which such an employee owes nothing (Payroll Tax Regulations, s. 2) —
  mark the contract exempt when the remuneration of the year is not
  expected to exceed it, and refund through an amended annual return a tax
  withheld below it; taxable benefits that are not part of the gross of
  the payslip; the annual reconciliation (annual return).
- The WSCC minimum assessment (200), the subclass rates, the Personal
  Optional Coverage of directors and owners and the split of the payroll
  of a worker who works in both territories are on the assessment, not in
  the payslips.
