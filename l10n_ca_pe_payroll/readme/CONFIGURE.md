Payroll > Configuration > Provincial Payroll Accounts, a record for Prince
Edward Island: the WCB PEI account number and the assessment rate per $100
that the board sends each January in the registration renewal package
(leave 0 without an account).

Installing the module adds the Prince Edward Island rules to the *Canada -
Base* structure of every company and, with the `ca_2023` chart, proposes
the accounts of the assessment (expense 512121, payable 221206).

On each contract whose province of employment is Prince Edward Island,
page *Canadian Payroll*, group *Provincial TD1*: the TD1PE claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other Prince Edward Island credits authorized by a tax services office and
the additional tax per pay; *Not Covered by Workers' Compensation* for a
proprietor, partner, independent operator, owner or director without
personal coverage, or a worker of an excluded industry.

## Parameters and their sources

| Code | 2026-01-01 | 2026-07-01 | 2027-01-01 | Use | Source |
|---|---|---|---|---|---|
| `l10n_ca.pe.brackets` | 9.5% / 13.47% from 33,928 / 16.6% from 65,820 / 17.62% from 106,890 / 19% from 142,520 | adds 21% from 200,000 (prorated) | 20% from 200,000 | V and KP of T4 | T4127 122nd edition, table 8.1 (fifth bracket "Updated May 2026"); 123rd edition, Prince Edward Island changes and table 8.1; Income Tax Act, s. 7 |
| `l10n_ca.pe.bpa` | 15,000 | | | TCP without a TD1PE | T4127 table 8.2, TD1PE 2026, Income Tax Act, s. 9(1)(c) |
| `l10n_ca.pe.wcb.max_insurable` | 89,300 | | | Assessable earnings of the year | WCB PEI Rates and Payments, Employer Registration; Workers Compensation Act, ss. 46-47 |

Constants KP derived by the engine: 0, 1,347, 3,407, 4,497, 6,464, then
10,464 from July 1, 2026 and 8,464 from January 1, 2027 for the bracket
above 200,000, as in the T4127 tables.

The January 2026 table of the T4127 carries the note "*Updated May 2026"
on the fifth threshold (142,520) and its constant (6,464): the revised
edition gives the threshold of s. 7(e) of the Income Tax Act. The
parameters ship the revised figures.

The 2027 version of the brackets only ends the proration: the Income Tax
Act and the 123rd edition state 20% above 200,000 for 2026 and the years
after. The basic personal amount and the WCB PEI maximum have no 2027
version: a 2027 pay uses those of 2026 and the payslip warns that the
amounts of 2027 are not entered until the January 2027 edition of T4127
is checked.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.095 x TCP;
  K2P = 0.095 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.095 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract. T2 = T4.
- From July 1 to December 31, 2026, the rate above 200,000 is 21%: 2 x
  20% - 19%, so that the year bears 20% when the pays of January to June
  withheld 19%.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- WCB PEI: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); assessment = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month: A = 59,435.04; T4 = 0.1347 x 59,435.04 - 1,347 - 1,425
  - 358.61 = 4,875.29; (5,338.29 + 4,875.29) / 12 = 851.13, of which
  444.86 federal and 406.27 Prince Edward Island.
- T4032 for Prince Edward Island, 1,300 a week with an RRSP of 80: 216.13
  (the CRA's total), 114.57 federal and 101.56 Prince Edward Island;
  1,600 a week above the YMPE: 334.46, 180.89 federal and 153.57 Prince
  Edward Island. The same totals with pays dated in July 2026.
- 20,000 a month (A = 237,635.04): 3,068.39 of Prince Edward Island tax
  in June (19% above 142,520), 3,131.11 in July (21% above 200,000); the
  annual T2 rises by 0.02 x 37,635.04 = 752.70. In 2027, T2 = 37,196.97
  at 20%.
- WCB PEI at 1.28 per $100, 10,000 a month: 128.00 a month until August,
  119.04 on the 9,300 left in September, nothing in October.

## Not covered

- The WCB PEI rate is the one of the company: the rate group, the
  experience rating, the minimum assessment and the personal coverage of
  proprietors are on the board's statement, not in the payslips.
- Excluded industries and workers outside the WCB PEI coverage are marked
  per contract (*Not Covered by Workers' Compensation*); the 10-day
  presence rule for non-resident workers is not computed.
- No 2027 maximum assessable earnings: the board announces it near the
  end of the year; the watcher reports it on the Rates and Payments page.
