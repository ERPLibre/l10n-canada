Payroll > Configuration > Provincial Payroll Accounts, a record for
Alberta: the WCB-Alberta account number and the premium rate per $100 of
assessable earnings of the employer (rate of its rate group adjusted by
its experience; leave 0 without an account).

Installing the module adds the Alberta rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the premium (expense 512121, payable 221206).

On each contract whose province of employment is Alberta, page
*Canadian Payroll*, group *Provincial TD1*: the TD1AB claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other Alberta credits authorized by a tax services office and the
additional tax per pay; *Not Covered by Workers' Compensation* for a
business owner, partner or director without optional personal coverage.

## Parameters and their sources

| Code | 2026 | Use | Source |
|---|---|---|---|
| `l10n_ca.ab.brackets` | 8% / 10% from 61,200 / 12% from 154,259 / 13% from 185,111 / 14% from 246,813 / 15% from 370,220 | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1; Alberta Personal Income Tax page |
| `l10n_ca.ab.bpa` | 22,769 | TCP without a TD1AB | T4127 step 4 and table 8.2, TD1AB 2026 |
| `l10n_ca.ab.supplemental_credit.threshold` | 4,896.00 | K5P | T4127 step 4, Alberta; T4032-AB |
| `l10n_ca.ab.supplemental_credit.rate` | 0.25 | K5P | T4127 step 4, Alberta; T4032-AB |
| `l10n_ca.ab.wcb.max_insurable` | 110,900 | Assessable earnings of the year | WCB-Alberta fact sheet WCB-615, 2026 board order |

Alberta did not change on July 1, 2026 (T4127 123rd edition), and no
Alberta figure for 2027 is published yet: the parameters have no 2027
version.

## Formulas

- A = the annual taxable income of the federal computation.
- T4 = V x A - KP - K1P - K2P - K3P - K5P, at least 0; K1P = 0.08 x TCP;
  K2P = 0.08 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum x
  PM / 12) + 0.08 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract.
- K5P = ((K1P + K2P) - 4,896.00) x 0.25, 0 if negative: the supplemental
  tax credit. 4,896 = 0.08 x 61,200 and 0.25 x 0.08 = 2%: the T4032-AB
  states it as 2% of the credit amounts (TD1AB claim, CPP and EI) above
  61,200, the difference between the second rate and the lowest one.
  For an employee transferred from Quebec during the year, K2P is the
  K2RP of the engine, as T4127 requires.
- T2 = T4 (Alberta has no surtax, premium, reduction or LCP).
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- WCB-Alberta: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); premium = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month: A = 59,434.99; T4 = 0.08 x 59,434.99 - 1,821.52 -
  301.98 = 2,631.30; (5,338.28 + 2,631.30) / 12 = 664.13, of which 444.86
  federal and 219.27 Alberta.
- T4032 for Alberta, 1,300 a week with an RRSP of 80: 170.20 (the CRA's
  total), 114.57 federal and 55.63 Alberta, no supplemental credit
  (K1P + K2P = 2,163.52).
- T4032 for Alberta, 1,600 a week above the YMPE with a TD1AB claim of
  60,000: K5P = (4,800 + 371.40 - 4,896) x 0.25 = 68.85; 210.18 (the
  CRA's total), 180.89 federal and 29.29 Alberta.
- 12,000 a month at 1.46 per $100: 175.20 of premium a month until the
  110,900 of assessable earnings are reached in October (2,900, 42.34).

## Not covered

- The WCB-Alberta minimum premium (200 a year per account), the rate
  group and experience rating, the personal coverage of business owners
  and the reconciliation of the annual return are on the WCB-Alberta
  account, not in the payslips.
- The tables of claim codes (T4127 table 8.10) are not used: the contract
  holds the TD1AB total claim amount itself (option 1).
