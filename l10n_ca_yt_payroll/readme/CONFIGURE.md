Payroll > Configuration > Provincial Payroll Accounts, a record for
Yukon: the WSCB account number and the assessment rate per $100 of the
rate group of the company for the year (leave 0 without an account).

Installing the module adds the Yukon rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the assessment (expense 512121, payable 221206).

On each contract whose province of employment is Yukon, page *Canadian
Payroll*: group *Provincial TD1*, the TD1YT claim (basic personal amount,
total claim amount, or exempt for claim code E), the other Yukon credits
authorized by a tax services office and the additional tax per pay; the
*Prescribed Zone Deduction (Annual)* of the TD1, which lowers A of the
federal and the Yukon tax; *Not Covered by Workers' Compensation* for a
proprietor, partner or Yukon First Nation official without optional
coverage, or a director deemed a non-working director.

## Parameters and their sources

| Code | 2026 | 2027 | Use | Source |
|---|---|---|---|---|
| `l10n_ca.yt.brackets` | 6.4% / 9% from 58,523 / 10.9% from 117,045 / 12.8% from 181,440 / 15% from 500,000 | | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1 |
| `l10n_ca.yt.bpa` | 16,452 | | Maximum BPAYT, shown on the contract | T4127 chapter 2 and table 8.2, TD1YT 2026 |
| `l10n_ca.federal.bpa_*` (federal module) | 16,452 / 14,829, 181,440 to 258,482 | | BPAYT of the pay | T4127 chapter 2 (BPAYT = BPAF) |
| `l10n_ca.federal.canada_employment_amount` (federal module) | 1,501 | | CEA of K4P | T4127 table 8.2 |
| `l10n_ca.yt.wcb.max_insurable` | 107,599 | 111,580 | Assessable earnings of the year | WSCB, maximum annual earnings |

Yukon did not change on July 1, 2026 (T4127 123rd edition); the 2027
Yukon tax figures are not published yet.

## Formulas

- A = the annual taxable income of the federal computation, P x (I - F -
  F2 - F5A - U1) - HD.
- BPAYT = 16,452 for NI = A + HD up to 181,440; 14,829 from 258,482;
  16,452 - (NI - 181,440) x 1,623 / 77,042 in between, rounded to the
  cent. TCP = BPAYT without a TD1YT, the total claim amount otherwise.
- T4 = V x A - KP - K1P - K2P - K3P - K4P, at least 0; K1P = 0.064 x TCP;
  K2P = 0.064 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.064 x (P x EI, at most the EI maximum); K3P = the other
  credits of the contract; K4P = min(0.064 x A*, 0.064 x 1,501), A* = P x
  the gross of the pay without its non-periodic payments.
- T2 = T4 (no surtax, premium, reduction or LCP in Yukon).
- Tax of the pay: (T1 + T2) / P rounded once; the territorial line is
  that total less the federal line, plus the additional tax of the
  contract.
- WSCB: assessable earnings of the pay = min(gross, maximum - assessable
  earnings of the year so far); premium = rate x assessable earnings /
  100.

## Worked examples (tests)

- 5,000 a month: A = 59,435.04; T4 = 0.09 x 59,435.04 - 1,522 - 1,052.93
  - 241.59 - 96.06 = 2,436.57; (5,338.29 + 2,436.57) / 12 = 647.91, of
  which 444.86 federal and 203.05 Yukon.
- T4032 for Yukon, 1,300 a week with an RRSP of 80 and a prescribed zone
  deduction of 4,015: 143.86 (the CRA's total), 98.75 federal and 45.11
  Yukon; 1,600 a week above the YMPE: 262.05, 180.89 federal and 81.16
  Yukon.
- 20,000 a month, inside the phase-out: A = 237,635.04, BPAYT =
  15,268.17, T2 = 21,853.94.

## Not covered

- The WSCB minimum assessment premium (150), the over-estimate fee and
  the optional coverage of proprietors are on the WSCB invoice, not in
  the payslips; the rate of a company with several rate groups is the
  single rate of its provincial payroll account.
- K4P counts the regular gross of the pay: on a bonus pay, the A* of
  T4127, which includes the bonus, only changes K4P when the regular
  annual gross is below the Canada employment amount.
- Claim codes (option 2) are not used: the TD1YT amount is entered as is.
