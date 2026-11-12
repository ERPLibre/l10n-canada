Payroll > Configuration > Provincial Payroll Accounts, a record for
Saskatchewan: the WCB account number and the industry premium rate per
$100 of the premium rate notice of the year, experience rating included
(leave 0 without an account).

Installing the module adds the Saskatchewan rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the premium (expense 512121, payable 221206).

On each contract whose province of employment is Saskatchewan, page
*Canadian Payroll*, group *Provincial TD1*: the TD1SK claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other Saskatchewan credits authorized by a tax services office and the
additional tax per pay; *Labour-Sponsored Fund Shares per Pay* for the
LCP credit; *Not Covered by Workers' Compensation* for a proprietor,
partner or director of a corporation (not a worker since January 1,
2025) without optional personal coverage.

## Parameters and their sources

| Code | 2026 | Use | Source |
|---|---|---|---|
| `l10n_ca.sk.brackets` | 10.5% / 12.5% from 54,532 / 14.5% from 155,805 | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1; Government of Saskatchewan, 2026 Personal Income Tax Structure |
| `l10n_ca.sk.bpa` | 20,381 | TCP without a TD1SK | T4127 What's new and table 8.2, TD1SK 2026, 2026 Personal Income Tax Structure |
| `l10n_ca.sk.lcp_rate`, `l10n_ca.sk.lcp_max` | 17.5%, 875 | LCP | T4127 step 5, Saskatchewan, and table 8.2 |
| `l10n_ca.sk.wcb.max_insurable` | 108,223 | Assessable earnings of the year | Saskatchewan WCB, Maximum assessable earnings |

No figure changes on July 1, 2026 (T4127 123rd edition). No 2027 version
is shipped: the 2027 basic personal amount (indexation plus 500 of The
Saskatchewan Affordability Act) and the 2027 WCB maximum are not
published yet. A pay of 2027 uses the 2026 amounts and warns about it.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.105 x TCP;
  K2P = 0.105 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.105 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract.
- T2 = T4 - P x LCP, at least 0; LCP = min(875, 0.175 x the shares
  withheld on the pay) and P x LCP at most 875.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- WCB: assessable earnings of the pay = min(gross, maximum - assessable
  earnings of the year so far); premium = rate x assessable earnings /
  100.

## Worked examples (tests)

- 5,000 a month: A = 59,435.04; T4 = 0.125 x 59,435.04 - 1,091 -
  2,140.005 - 396.35 = 3,802.02; (5,338.29 + 3,802.02) / 12 = 761.69, of
  which 444.86 federal and 316.83 Saskatchewan.
- T4032 for Saskatchewan, 1,300 a week with an RRSP of 80: 194.77 (the
  CRA's total), 114.57 federal and 80.20 Saskatchewan; 1,600 a week above
  the YMPE: 301.38, 180.89 federal and 120.49 Saskatchewan.
- 100 of labour-sponsored fund shares a month: P x LCP = 210,
  Saskatchewan tax 299.33.
- 13,000 a month at a WCB rate of 1.22: 158.60 a month; September takes
  the 4,223 left below 108,223 (51.52), October bears no premium.

## Not covered

- The WCB minimum premium, the experience rating and the optional
  personal coverage of proprietors are on the premium rate notice and the
  statement of account, not in the payslips.
- The prorated maximum of a worker employed in several provinces
  (Saskatchewan gross / total gross x maximum) is not computed: each
  province's maximum applies to the earnings of that province.
- The LCP of a year is capped per pay as T4127 does (P x LCP at most the
  maximum); the shares bought in previous pays of the year are not
  counted.
