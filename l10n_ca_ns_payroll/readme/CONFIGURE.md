Payroll > Configuration > Provincial Payroll Accounts, a record for Nova
Scotia: the WCB Nova Scotia account number and the rate per $100 of
assessable payroll that the board notifies each September 1 for the next
year (leave 0 without an account).

Installing the module adds the Nova Scotia rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the premium (expense 512121, payable 221206).

On each contract whose province of employment is Nova Scotia, page
*Canadian Payroll*, group *Provincial TD1*: the TD1NS claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other Nova Scotia credits authorized by a tax services office and the
additional tax per pay; *Labour-Sponsored Fund Shares per Pay* for the
LCP credit; *Not Covered by Workers' Compensation* for a proprietor or
partner without optional coverage.

## Parameters and their sources

| Code | 2026 | 2027 | Use | Source |
|---|---|---|---|---|
| `l10n_ca.ns.brackets` | 8.79% / 14.95% from 30,995 / 16.67% from 61,991 / 17.5% from 97,417 / 21% from 157,124 | | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1; Nova Scotia Finance |
| `l10n_ca.ns.bpa` | 11,932 | | TCP without a TD1NS | T4127 table 8.2, TD1NS 2026, Nova Scotia Finance |
| `l10n_ca.ns.lcp_rate`, `l10n_ca.ns.lcp_max` | 20%, 2,000 | | LCP | T4127 step 5, Nova Scotia |
| `l10n_ca.ns.wcb.max_insurable` | 79,900 | 83,300 | Assessable earnings of the year | WCB Nova Scotia; Workers' Compensation Act s. 41; General Regulations s. 22 |

The July 2026 edition of T4127 changes nothing for Nova Scotia; no 2027
income tax figure is published yet.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.0879 x TCP;
  K2P = 0.0879 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.0879 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract.
- TCP without a TD1NS is the basic personal amount whatever the income:
  T4127 removes the income-tested BPANS formula for 2026.
- T2 = T4 - P x LCP, at least 0; LCP = min(2,000, 0.20 x the shares
  withheld on the pay) and P x LCP at most 2,000.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- WCB Nova Scotia: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); premium = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month: A = 59,435.04; T4 = 0.1495 x 59,435.04 - 1,909 -
  1,048.82 - 331.80 = 5,595.92; (5,338.29 + 5,595.92) / 12 = 911.18, of
  which 444.86 federal and 466.32 Nova Scotia.
- T4032 for Nova Scotia, 1,300 a week with an RRSP of 80: 231.27 (the
  CRA's total), 114.57 federal and 116.70 Nova Scotia; 1,600 a week above
  the YMPE: 351.70, 180.89 federal and 170.81 Nova Scotia.
- 100 of labour-sponsored fund shares a month: P x LCP = 240, Nova Scotia
  tax 446.32.
- WCB Nova Scotia at 2.65 per $100, 10,000 a month: 265.00 a month until
  July, 262.35 on the 9,900 left in August, nothing from September.

## Not covered

- The rate of the employer (industry rate, experience rating, safety
  association levy, surcharge) comes from the board's notice, not from
  the payslips.
- The LCP of a year is capped per pay as T4127 does (P x LCP at most the
  maximum); the shares bought in previous pays of the year are not
  counted.
- No official page states in so many words that Nova Scotia has no
  employer payroll tax: the module relies on the absence of such a tax
  from the provincial tax pages.
