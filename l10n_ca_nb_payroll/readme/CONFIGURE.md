Payroll > Configuration > Provincial Payroll Accounts, a record for New
Brunswick: the WorkSafeNB account number and the assessment rate per $100
of the assessment notice of the year (leave 0 without an account).

Installing the module adds the New Brunswick rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the assessment (expense 512121, payable 221206).

On each contract whose province of employment is New Brunswick, page
*Canadian Payroll*, group *Provincial TD1*: the TD1NB claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other New Brunswick credits authorized by a tax services office and the
additional tax per pay; *Labour-Sponsored Fund Shares per Pay* for the
LCP credit; *Not Covered by Workers' Compensation* for a proprietor,
partner or non-salaried officer without optional coverage.

## Parameters and their sources

| Code | 2026 | 2027 | Use | Source |
|---|---|---|---|---|
| `l10n_ca.nb.brackets` | 9.4% / 14% from 52,333 / 16% from 104,666 / 19.5% from 193,861 | | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1 |
| `l10n_ca.nb.bpa` | 13,664 | | TCP without a TD1NB | T4127 table 8.2, TD1NB 2026 |
| `l10n_ca.nb.lcp_rate`, `l10n_ca.nb.lcp_max` | 20%, 2,000 | | LCP | T4127 step 5, New Brunswick |
| `l10n_ca.nb.wcb.max_insurable` | 85,800 | 88,200 | Assessable earnings of the year | WorkSafeNB |

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.094 x TCP;
  K2P = 0.094 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.094 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract.
- T2 = T4 - P x LCP, at least 0; LCP = min(2,000, 0.20 x the shares
  withheld on the pay) and P x LCP at most 2,000.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- WorkSafeNB: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); assessment = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month: A = 59,434.99; T4 = 0.14 x 59,434.99 - 2,407 - 1,284.42
  - 354.83 = 4,274.65; (5,338.28 + 4,274.65) / 12 = 801.08, of which
  444.86 federal and 356.22 New Brunswick.
- T4032 for New Brunswick, 1,300 a week with an RRSP of 80: 204.93 (the
  CRA's total), 114.57 federal and 90.36 New Brunswick; 1,600 a week above
  the YMPE: 316.55, 180.89 federal and 135.66 New Brunswick.
- 100 of labour-sponsored fund shares a month: P x LCP = 240, New
  Brunswick tax 336.22.

## Not covered

- The WorkSafeNB minimum assessment (150), the experience rating and the
  personal coverage of proprietors are on the assessment notice, not in
  the payslips.
- The LCP of a year is capped per pay as T4127 does (P x LCP at most the
  maximum); the shares bought in previous pays of the year are not
  counted.
