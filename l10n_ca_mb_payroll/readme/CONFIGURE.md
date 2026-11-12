Payroll > Configuration > Provincial Payroll Accounts, a record for
Manitoba:

- the levy account number; *Rate Basis* and the total Manitoba
  remuneration of the previous year, or the estimate of the current year
  for a new employer or a payroll that changes, before the exemption: it
  selects the rate (4.3% up to 5,000,000, 2.15% above) and whether the
  exemption applies;
- a member of an associated group (associated corporations, corporate
  partnerships) ticks *Associated Employer*, enters the COMBINED
  remuneration of the group as the rate basis and its share of the
  2,500,000 exemption as *Exemption Allocated to the Company* (0 when the
  group exceeds 5,000,000);
- leave *Registered Charity* unticked: the Act keeps no exemption for a
  charity above 5,000,000;
- the WCB Manitoba account number and the premium rate per $100 of the
  assessment of the year (leave 0 without an account).

Installing the module adds the Manitoba rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the levy and of the premium (expense 512121, payable
221206).

On each contract whose province of employment is Manitoba, page
*Canadian Payroll*, group *Provincial TD1*: the TD1MB claim (basic
personal amount, total claim amount, or exempt for claim code E), the
other Manitoba credits authorized by a tax services office and the
additional tax per pay; *Labour-Sponsored Fund Shares per Pay* for the
LCP credit; *Not Covered by Workers' Compensation* for a director, sole
proprietor or partner without personal coverage.

## Parameters and their sources

| Code | 2026 | Use | Source |
|---|---|---|---|
| `l10n_ca.mb.brackets` | 10.8% / 12.75% from 47,000 / 17.4% from 100,000 | V and KP of T4 | T4127 122nd and 123rd editions, table 8.1; Manitoba Finance |
| `l10n_ca.mb.bpa` | 15,780 | Maximum BPAMB | T4127 chapter 2 and table 8.2, TD1MB 2026 |
| `l10n_ca.mb.bpa_phaseout_start`, `l10n_ca.mb.bpa_phaseout_end` | 200,000, 400,000 | Phase-out of BPAMB | T4127 chapter 2, BPAMB formula |
| `l10n_ca.mb.lcp_rate`, `l10n_ca.mb.lcp_max` | 15%, 1,800 | LCP | T4127 step 5, Manitoba |
| `l10n_ca.mb.employer_tax.rates` | 4.3%; 2.15% above 5,000,000 | Levy rate | Act C.C.S.M. c. H24, s. 3; Manitoba Finance; Bulletin HE 001 |
| `l10n_ca.mb.employer_tax.exemption` | 2,500,000 | Levy exemption | Act s. 3(3.12); Bulletin HE 001 |
| `l10n_ca.mb.employer_tax.exemption_threshold` | 5,000,000 | End of the notch range | Act s. 3(3.14); Bulletin HE 001 |
| `l10n_ca.mb.wcb.max_insurable` | 171,500 | Assessable earnings of the year | WCB Manitoba fact sheet; Act C.C.S.M. c. W200, s. 46(2) |

Manitoba does not index its brackets and BPAMB from 2025, and did not
change on July 1, 2026. No 2027 version is shipped: the T4127 of July
2026 announces no Manitoba change for 2027, the levy amounts of the Act
have no end date, and WCB Manitoba has not published its 2027 maximum. A
2027 payslip warns that the 2026 BPAMB is used until a 2027 version is
entered.

## Formulas

- A = the annual taxable income of the federal computation; NI of the
  BPAMB formula = A.
- BPAMB = 15,780 for A up to 200,000; 15,780 - (A - 200,000) x (15,780 /
  200,000) between 200,000 and 400,000, the division not rounded and the
  result rounded half up to the cent; 0 from 400,000.
- T4 = V x A - KP - K1P - K2P - K3P, at least 0; K1P = 0.108 x TCP (TCP =
  BPAMB without a TD1MB); K2P = 0.108 x (P x C x 0.0495 / 0.0595, at most
  the base CPP maximum x PM / 12) + 0.108 x (P x EI, at most the EI
  maximum); K3P = the other credits of the contract.
- T2 = T4 - P x LCP, at least 0; LCP = min(1,800, 0.15 x the shares
  withheld on the pay) and P x LCP at most 1,800.
- Tax of the pay: (T1 + T2) / P rounded once; the provincial line is that
  total less the federal line, plus the additional tax of the contract.
- Levy of a pay: rate x (max(0, R + G - E) - max(0, R - E)), R the
  Manitoba remuneration the company paid before the pay in the year, G
  the gross of the pay, E the exemption. With a rate basis up to
  5,000,000: rate 4.3%, E = 2,500,000, so the year totals 4.3% x (R -
  2,500,000); above: rate 2.15%, E = 0, so the year totals 2.15% x R.
  Both give 107,500 at 5,000,000.
- WCB Manitoba: assessable earnings of the pay = min(gross, maximum -
  assessable earnings of the year so far); premium = rate x assessable
  earnings / 100.

## Worked examples (tests)

- 5,000 a month: A = 12 x (5,000 - 47.08) = 59,435.04; T4 = 0.1275 x
  59,435.04 - 917 - 1,704.24 - 407.68 = 4,549.05; (5,338.29 + 4,549.05)
  / 12 = 823.95, of which 444.86 federal and 379.09 Manitoba.
- T4032 for Manitoba, 1,300 a week with an RRSP of 80: 209.26 (the
  CRA's total), 114.57 federal and 94.69 Manitoba; 1,600 a week above
  the YMPE: 316.68, 180.89 federal and 135.79 Manitoba.
- 25,000 a month without CPP and EI: A = 300,000, BPAMB = 7,890, T4 =
  0.174 x 300,000 - 5,567 - 852.12 = 45,780.88; 3,815.07 Manitoba.
- 100 of labour-sponsored fund shares a month: P x LCP = 180, Manitoba
  tax 364.09.
- Levy, rate basis 5,000,000, five pays of 1,000,000: 0, 0, 21,500,
  43,000, 43,000, that is 107,500 for the year.

## Not covered

- Proration of the levy exemption and notch range for an employer
  without a permanent establishment in Manitoba for the whole year (Act
  s. 3(3.15)), and the pre-association proration of s. 3(3.10).
- The levy of the year is settled on the ACTUAL remuneration by the
  annual report; the payslips use the rate and exemption of the rate
  basis entered on the account, and a year whose actual remuneration
  crosses 2,500,000 or 5,000,000 differently from the basis is adjusted
  by that report, not by the payslips.
- Remuneration of employees of a Manitoba establishment whose province
  of employment on the contract is not Manitoba is not counted in the
  levy.
- The WCB Manitoba minimum charge (100 a year), the experience rating and
  the personal coverage of directors, proprietors and partners are on the
  assessment, not in the payslips.
- The deduction for living in a prescribed zone (HD of T4127): NI of the
  BPAMB formula is A.
- The LCP of a year is capped per pay as T4127 does (P x LCP at most the
  maximum); the shares bought in previous pays of the year are not
  counted.
