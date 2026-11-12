Payroll > Configuration > Settings > Ontario Payroll:

- *Employer Health Tax*: the EHT account number; whether the company is an
  eligible employer (public-sector employers, Crown bodies and the other
  persons the Act excludes are not, and pay the tax on their whole Ontario
  remuneration); whether it is a registered charity (it keeps its
  exemption whatever its remuneration); whether it is associated with other
  employers, and then the share of the group exemption allocated to it by
  the agreement of the group (0 when the remuneration of the group exceeds
  5,000,000); the rate basis, the total Ontario remuneration of the
  previous year or an estimate of the current year, all accounts combined
  and before the exemption, and its amount;
- *WSIB*: the account number and the premium rate per $100 of insurable
  earnings of the rate notice of the year (leave 0 without a WSIB
  account).

Installing the module adds the Ontario rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts of the employer contributions (expense 512121, payable 221206).
The *Set Up Canadian Payroll* button does the same for a new company.

On each contract whose province of employment is Ontario, page *Canadian
Payroll*: the TD1ON claim (basic personal amount, total claim amount of
line 10 of the form, or exempt for claim code E), the dependants under age
19 and the disabled dependants of the tax reduction (from a written or
electronic request of the employee: the TD1ON 2026 no longer has that
section), the other Ontario credits authorized by a tax services office,
the additional Ontario tax per pay, and *Not Covered by the WSIB* for an
executive officer outside construction without optional insurance. A
non-resident whose federal claim is 0 has an Ontario claim of 0 as well
(total claim amount 0): the module has no non-resident flag to set it. The
federal fields of the same page apply as well: RPP, RRSP, union dues and
support payments lower the annual taxable income A of both the federal and
the Ontario tax.

Payroll > Configuration > Canadian Time Parameters: add a version when the
CRA publishes the T4127 of a new year (usually in November or December).

## Parameters and their sources

Every rate, ceiling, bracket table and credit amount the Ontario
computation uses is a dated time parameter (Payroll > Configuration >
Canadian Time Parameters). A new year is a new version of the parameter,
dated January 1. A parameter keeps its last version until a later one
replaces it. A payslip reads the version in force at its pay date. Each
parameter's record also carries its source URLs in its description; the
page `static/description/sources.html` lists them by source.

The Ontario tax uses the federal parameters of `l10n_ca_payroll` for the
contributions (CPP, EI) and for the annual taxable income A, and the
federal flat rate on a bonus (`l10n_ca.federal.bonus_flat_threshold`,
`l10n_ca.federal.bonus_flat_rate`).

### Sources

- CRA, *T4127 Payroll Deductions Formulas*, 122nd edition, effective
  January 1, 2026: the Ontario formulas of steps 4 and 5 (T4, K1P, K2P, T2)
  and of the Ontario section (V1, V2, S), table 8.1 (2026 brackets and
  constants), table 8.2 (2026 basic personal amount, S2, surtax), tables
  8.22 and 8.23 (the same for 2025):
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jan/t4127-jan-payroll-deductions-formulas-computer-programs.html>.
  The 123rd edition, effective July 1, 2026, lists Ontario without change
  and carries the same figures and formulas:
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jul/t4127-jul-payroll-deductions-formulas.html>.
- CRA, T4127 120th edition, effective January 1, 2025: the 2025 Ontario
  figures, among them the 544 per dependant of the tax reduction that the
  122nd edition does not repeat:
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/payroll-deductions-t4127-payroll-deductions-formulas/t4127-jan-120th-edition-effective-january-1-2025/t4127-jan-payroll-deductions-formulas-computer-programs.html>.
  The 121st edition, effective July 1, 2025, lists Ontario without change:
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/payroll-deductions-t4127-payroll-deductions-formulas/t4127-jul-121st-edition-effective-july-1-2025/t4127-jul-payroll-deductions-formulas.html>.
- CRA, TD1ON 2026, *Ontario Personal Tax Credits Return*, line 1:
  <https://www.canada.ca/content/dam/cra-arc/formspubs/pbg/td1on/td1on-26e.pdf>.
- Government of Ontario, *2026 Ontario Economic Outlook and Fiscal Review*,
  tax provisions (tax reduction 300 and 554 per dependent child; EHT
  exemption of 1 million):
  <https://budget.ontario.ca/2026/fallstatement/provisions.html>.
- *Employer Health Tax Act*, R.S.O. 1990, c. E.11, s. 1(1) (remuneration,
  total Ontario remuneration), 2(2) and its table (rates), 2.1 (exemption,
  exemption threshold, associated employers, charities), 3 (instalments)
  and 5 (annual return): <https://www.ontario.ca/laws/statute/90e11>.
- Ontario Ministry of Finance, *Employer Health Tax (EHT)*:
  <https://www.ontario.ca/document/employer-health-tax-eht>, with its pages
  on associated employers, remuneration and filing.
- WSIB, premium rates of the year:
  <https://www.wsib.ca/en/2025premiumrates>,
  <https://www.wsib.ca/en/2026premiumrates>,
  <https://www.wsib.ca/en/2027premiumrates>; *How to calculate your
  premium and insurable earnings*:
  <https://www.wsib.ca/en/businesses/premiums-and-payment/how-calculate-your-premium-and-insurable-earnings>;
  *Policy in practice: premium reporting frequency*:
  <https://www.wsib.ca/en/policy-practice-premium-frequency>; *How to
  report and pay your premiums*:
  <https://www.wsib.ca/en/businesses/premiums-and-payment/how-report-and-pay-your-premiums>.
- *Workplace Safety and Insurance Act, 1997*, s. 11(2), 12, 54(1), 87 and
  88: <https://www.ontario.ca/laws/statute/97w16>.

### Ontario income tax

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.on.brackets` | 5.05% to 52,886; 9.15% to 105,775; 11.16% to 150,000; 12.16% to 220,000; 13.16% above | 5.05% to 53,891; 9.15% to 107,785; 11.16% to 150,000; 12.16% to 220,000; 13.16% above | V is the rate of the bracket of A; KP is derived from the table and rounded to the dollar like the federal K (2026: 0, 2,210, 4,376, 5,876, 8,076; 2025: 0, 2,168, 4,294, 5,794, 7,994). The rate of the first bracket is the lowest Ontario rate of K1P and K2P. | T4127 122nd edition tables 8.1 and 8.22; 120th edition table 8.1 |
| `l10n_ca.on.bpa` | 12,747 | 12,989 | TCP without a TD1ON: K1P = 0.0505 x TCP (2026: 655.94). | T4127 tables 8.2 and 8.23; TD1ON 2026 |
| `l10n_ca.on.surtax` | 20% above 5,710; 36% above 7,307 | 20% above 5,818; 36% above 7,446 | V1 = 0.20 x (T4 - first threshold) + 0.36 x (T4 - second threshold), each term when T4 exceeds its threshold. | T4127 Ontario section, tables 8.2 and 8.23 |
| `l10n_ca.on.tax_reduction_basic` | 294 | 300 | S2 of S = min(T4 + V1, 2 x (S2 + Y) - (T4 + V1)), at least 0. | T4127 Ontario section, tables 8.2 and 8.23; Fall Statement 2026 |
| `l10n_ca.on.tax_reduction_dependant` | 544 | 554 | Y = amount x (dependants under age 19 + disabled dependants) of the contract. | T4127 Ontario section (2025: 120th edition; 2026: 122nd edition); Fall Statement 2026 |
| `l10n_ca.on.health_premium` | schedule below | same | V2 on A, not reduced by S, withheld even with claim code E. | T4127 Ontario section |

The Ontario Health Premium schedule, not indexed, is the same in 2025 and
2026: V2 = 0 up to A = 20,000; min(300, 0.06 x (A - 20,000)) up to 36,000;
min(450, 300 + 0.06 x (A - 36,000)) up to 48,000; min(600, 450 + 0.25 x
(A - 48,000)) up to 72,000; min(750, 600 + 0.25 x (A - 72,000)) up to
200,000; min(900, 750 + 0.25 x (A - 200,000)) above.

The formulas:

- T4 = V x A - KP - K1P - K2P - K3P, at least 0. K4P and K5P are 0 for
  Ontario, and Ontario has no labour-sponsored funds credit (LCP).
- K1P = 0.0505 x TCP, TCP being the Ontario basic personal amount or the
  total claim amount of the TD1ON entered on the contract.
- K2P = 0.0505 x (P x C x 0.0495 / 0.0595, at most the base CPP maximum
  x PM / 12) + 0.0505 x (P x EI, at most the EI maximum): the K2 items of
  the federal module at the lowest Ontario rate, with the same maximums
  (2026: 3,519.45 and 1,123.07; 2025: 3,356.10 and 1,077.48) and the same
  treatment once a maximum is reached in the year. For an employee
  transferred from Quebec during the year, the federal module adds DQ x
  (0.0530 - 0.0495) / 0.0630 to the base CPP maximum, DQ being the QPP
  withheld before the transfer: K2P is then the K2RP of T4127.
- K3P = the other Ontario credits of the contract (annual credit amount).
- T2 = T4 + V1 + V2 - S, at least 0. T4127 rounds the tax of the pay
  once, (T1 + T2) / P: the Ontario line is that total less the federal
  line, T1 / P rounded on its own, plus the additional Ontario tax of the
  contract. At 5,000 a month, (5,338.28 + 2,981.73) / 12 = 693.33, of
  which 444.86 federal and 248.47 Ontario.
- Claim code E: T2 = V2.
- Bonus, retroactive pay or other non-periodic payment: TB = T2 of A with
  the payment less T2 of A without it, each T2 recomputed in full (T4, V1,
  V2, S), A being the one of the federal bonus computation and K2P adding
  the contributions on the payment once. A without the payment is P x (I -
  F - F2 - F5A - U1) + B1 - F5BYTD; a pay of non-periodic payments alone
  takes I, F, F2, U1 and F5A of the most recent regular pay, as T4127 asks,
  while its K2P without the payment stays 0, as the federal K2. When A
  with the payment is at most 5,000, T4127 withholds 15% of the payment for the federal and the
  provincial tax together; the federal module withholds it on the federal
  line and the Ontario line stays at 0. K2P takes the K2 items of the
  federal module, which do not add the contributions withheld on the
  earlier non-periodic payments of the year (T4127 adds them to both
  steps); TB only moves when an annual maximum or a bracket is crossed.

The 2027 Ontario figures are not published: until a January 2027 version
is added, a 2027 pay uses the 2026 versions and its payslip warns that
`l10n_ca.on.bpa` has no version of its year. The announced cut of the base
CPP rate for 2027 changes the K2P ratio through the federal parameters.

### Employer Health Tax

| Parameter | 2025 | 2026 | 2027 | What the computation does with it | Source |
|---|---|---|---|---|---|
| `l10n_ca.on.eht.rates` | 0.98% up to 200,000; 1.101%, 1.223%, 1.344%, 1.465%, 1.586%, 1.708%, 1.829% by steps of 30,000 (the last 380,000 to 400,000); 1.95% above 400,000 | same | same | A single rate, the one of the annual total Ontario remuneration before the exemption, applied to the whole taxable remuneration. A remuneration equal to a threshold takes the lower rate. | EHT Act s. 2(2) and table |
| `l10n_ca.on.eht.exemption` | 1,000,000 | 1,000,000 | 1,000,000 | Exemption of an eligible employer; an associated employer takes the lesser of its allocated share and this amount. Fixed by the Act for 2020 to 2028. | EHT Act s. 2.1(2), (4.0.1) to (4.0.4) |
| `l10n_ca.on.eht.exemption_threshold` | 5,000,000 | same | same | Above it, an eligible employer that is neither associated nor a charity has no exemption. | EHT Act s. 2.1(5), (7), (9) |
| `l10n_ca.on.eht.instalment_threshold` | 1,200,000 | same | same | Above it, monthly instalments (documentation only). | EHT Act s. 3 |

Accrual of each pay: EHT = rate x (max(0, R + G - E) - max(0, R - E)),
where G is the gross of the pay, R the Ontario remuneration of the company
paid before it this year and E the exemption. The first pays of the year
consume the exemption; the pays after it bear the tax on their whole
remuneration. G keeps its sign: a recovery entered as negative earnings
lowers R and reverses the EHT on the part above E it takes back; a refund
(credit note) of a payslip counts negatively in R. A credit-note payslip
computed by the rules (a batch or a payslip marked as a credit note)
takes its gross out of R: its EHT line is rate x (max(0, R - E) - max(0,
R - G - E)), the tax of the last G of R, which counts negatively.

R counts the done payslips outside the batch of the pay and, in a batch,
the payslips that come before the pay and are not cancelled, whatever
their state: those with an earlier pay date, or the same pay date and
created before. Each pair of payslips of a batch is counted once, whatever
order the batch is confirmed in. A payslip outside a batch only counts
once done: payslips outside a batch computed side by side each see the
same exemption left. Confirming them recomputes them one after the other
and corrects this, unless *Prevent Compute on Confirm* is set in the
payroll settings; in that case, put them in a batch, or confirm each one
before computing the next.

A rate basis left at 0 gives the lowest rate and, unless the employer is
associated or not eligible, the exemption: the payslip warns about it.
The rate basis, the remuneration of the previous year or the estimate,
and the WSIB rate are company fields without a date: a payslip computed
today uses them whatever its year. Recompute a payslip of a previous year
before entering the values of the new year, or put the values of its year
back while recomputing it.
The remuneration is the gross of the payslip (salaries, wages, bonuses and
taxable benefits entered as earnings); severance pay that is a retiring
allowance is not remuneration for the EHT and must be left out of the
Ontario payslips or corrected on the return.

What the module does not compute: the proration of the exemption and of
the exemption threshold by the days of a partial year, the allocation of
the exemption between several accounts of one employer, the
designated-member rules of partnerships, and the remuneration of an
employee who reports to an establishment outside Ontario for all or
substantially all of the year. The annual return recomputes the tax on
the actual total Ontario remuneration: the difference with the accrued
lines, which use the rate of the basis, is settled there.

Instalments and return:

- an employer whose total Ontario remuneration for the year exceeds
  1,200,000 pays monthly instalments: once its cumulative remuneration
  exceeds the exemption, the tax on the remuneration of each month is due
  on the 15th of the following month (next business day for a weekend or a
  holiday). The 15th is the guidance of the Ministry of Finance (the
  regulation is R.R.O. 1990, Reg. 398);
- an employer at or below 1,200,000 pays the tax of the year with the
  annual return;
- the annual return and the unpaid balance are due on or before March 15
  of the following year (EHT Act s. 5(1) and (11)), as is the allocation
  agreement of a group of associated employers (s. 2.1(14));
- a final return is due within 40 days of the closure of the business and,
  from the 2026 tax year, within six months of an amalgamation if earlier
  than March 15.

### WSIB

| Parameter | 2025 | 2026 | 2027 | What the computation does with it | Source |
|---|---|---|---|---|---|
| `l10n_ca.on.wsib.max_insurable` | 117,000 | 121,700 | 126,700 | Insurable earnings of the pay IE = min(gross, maximum - IE of the year so far), at least 0; premium = rate per $100 x IE / 100. The IE of the year so far counts the payslips of the employee as R counts those of the company for the EHT, so two payslips of the employee in a batch share the maximum. A credit-note payslip reverses IE = min(G, IE so far - min(maximum, S - G)), at least 0, S being the Ontario remuneration of the employee so far. | WSIB premium rates pages; WSIA s. 54(1) and 88(3) |

The rate per $100 is set for each employer by the annual rate notice of the
WSIB (risk band of its class), so it is a field of the company and not a
time parameter. The provincial average rates (1.25 for 2025, 1.23 for 2026,
1.18 for 2027) are for information only. Schedule 2 employers pay the cost
of their claims instead of a premium: leave their rate at 0.

Reporting frequency, from the estimated annual insurable earnings of the
legal entity, all accounts combined:

- monthly from 1,000,000; the monthly reporters also file an annual
  reconciliation by March 31 of the following year;
- quarterly from 20,000 to 999,999.99;
- annual below 20,000, on estimated earnings, by the end of April.

Due dates of the reports: quarterly at the end of the month after each
quarter (April 30, July 31, October 31 and January 31; months confirmed,
days to confirm against the WSIB page *How to report and pay your
premiums*), monthly at the end of the following month (to confirm against
the same page). The module does not move a due date that falls on a
weekend or a holiday.

### Worked examples

The tests of the module assert the following amounts with the shipped
parameters. Each pay is monthly (P = 12), in 2026, in Ontario, with the
basic personal amount, unless stated otherwise.

- **5,000 a month**: C = 280.15, EI = 81.50, A = 12 x (5,000 - 280.15 x
  0.01 / 0.0595) = 59,434.99, federal tax 444.86. V = 0.0915, KP = 2,210,
  K1P = 655.94, K2P = 0.0505 x (2,796.79 + 978) = 190.63, T4 = 0.0915 x
  59,434.99 - 2,210 - 655.94 - 190.63 = 2,381.73, V1 = 0, V2 = 600, S = 0,
  T2 = 2,981.73: Ontario tax 248.48. Box 22 of the T4 = 693.34.
- **Tax reduction**: 2,800 a month, A = 33,298.99, K2P = 102.90, T4 =
  922.75, V2 = 300. Without dependant, S = 0 and the tax is 101.90; with
  one dependant under 19, S = 2 x (300 + 554) - 922.75 = 785.25, T2 =
  437.50 and the tax is 36.46. At 2,500 a month with one dependant under
  19 and one disabled dependant, S cancels T4 = 754.73 and only V2 = 300
  remains: 25.00.
- **Surtax**: 15,000 a month, A = 178,234.99, V = 0.1216, KP = 5,876,
  K2P = 0.0505 x (3,519.45 + 1,123.07) = 234.45, T4 = 14,906.98, V1 =
  0.20 x 9,088.98 + 0.36 x 7,460.98 = 4,503.75, V2 = 750, T2 = 20,160.73:
  1,680.06.
- **Claim code E**: 3,000 a month, A = 35,674.99, only V2 = 300 is
  withheld: 25.00. At 1,500 a month, A = 17,854.99 and nothing is withheld.
- **TD1ON claim 0, other credits 120 and additional tax 20**: T4 =
  2,917.67, T2 = 3,517.67: 293.14 + 20.00 = 313.14.
- **Union dues of 50**: A = 58,834.99, T4 = 2,326.83, T2 = 2,926.83:
  243.90.
- **Bonus of 3,000 on a pay of 5,000**: C = 458.65, EI = 130.40, F5B =
  28.91. Regular A = 59,421.87, T2 = 2,980.53: 248.38. With the bonus, A =
  62,392.96, K2P = 0.0505 x 3,972.19 = 200.60, T2 = 3,242.42: TB = 261.89.
  The federal tax is 444.63 + 581.44.
- **Bonus alone**: after three pays of 5,000, a pay of a bonus of 10,000
  without salary: A without = 59,434.99 (March), A with = 69,337.91, K2P
  with = 0.0505 x 643.57 = 32.50: TB = 0.0915 x 9,902.92 - 32.50 = 873.62.
- **Transfer from Quebec**: 10,000 a month, January to June in Quebec (QPP
  3,669.78), then Ontario. In September both maximums are reached: K2RP =
  0.0505 x (3,519.45 + 203.88 + 1,123.07) = 244.74, A = 120,000, T2 =
  9,565.73: 797.14.
- **Bonus with A at most 5,000**: 200 a month and a bonus of 1,000: 150.00
  federal, 0 Ontario.
- **2025**: 5,000 a month in March 2025, EI = 82.00, KP = 2,168, K1P =
  643.72, K2P = 190.93, T4 = 2,435.65, T2 = 3,035.65: 252.97. At 15,000 a
  month, K2P = 0.0505 x (3,356.10 + 1,077.48) = 223.90, T4 = 15,011.76,
  V1 = 4,634.06, T2 = 20,395.82: 1,699.65.
- **EHT across the exemption**: an associated employer with an allocated
  exemption of 12,000 and an estimated remuneration of 300,000 (rate
  1.465%), 5,000 a month: January and February bear no EHT, March 3,000 x
  1.465% = 43.95, April 5,000 x 1.465% = 73.25. A recovery of 2,000 in
  April instead gives -2,000 x 1.465% = -29.30, one of 4,000 only reverses
  the 3,000 above the exemption: -43.95. Once March is refunded, April
  bears 3,000 x 1.465% = 43.95. Two payslips of 5,000 in a batch with
  5,000 of exemption left: 0 and 73.25, in either confirmation order. With a previous-year
  remuneration of 6,000,000 the exemption is nil: 5,000 x 1.95% = 97.50.
  A non-eligible employer with 150,000: 5,000 x 0.98% = 49.00. In a
  batch, a payslip paid on March 15 takes the exemption of 5,000 before
  one paid on March 31 created earlier: 0 and 73.25. A credit-note payslip
  of March after January to March: 43.95, the EHT of March reversed, and
  April then bears 43.95.
- **WSIB**: rate 1.30, 50,000 a month in 2026: insurable earnings 50,000,
  50,000, 21,700, 0 and premiums 650.00, 650.00, 282.10, 0; two March
  payslips of the employee in one batch: 21,700 and 0. A credit-note
  payslip of March reverses 21,700 (282.10) and April then takes 21,700
  again. In 2025, 100,000 a month: 1,300.00 then 17,000 x 1.30% = 221.00.

### Updating for a new year

- Read the January T4127 of the year (Ontario rows of tables 8.1 and 8.2,
  Ontario section of step 5) and add the versions of
  `l10n_ca.on.brackets`, `l10n_ca.on.bpa`, `l10n_ca.on.surtax`,
  `l10n_ca.on.tax_reduction_basic` and
  `l10n_ca.on.tax_reduction_dependant` dated January 1. Check that the KP
  derived from the brackets equals the KP of table 8.1. Check the July
  edition for an Ontario change.
- Add the maximum insurable earnings of the WSIB page of the year, and
  enter the rate of the new rate notice on the company.
- The EHT exemption is indexed every five years from 2029: add the new
  amount when the Ministry of Finance publishes it.
- The TD1ON amount of a contract is not indexed by the payslip: enter the
  amount of the new form, or switch the contract to the basic personal
  amount.
- Run `python3 l10n_ca_payroll/tools/sources_page.py l10n_ca_on_payroll`
  after a change to the sources or to the parameter descriptions.

### Not covered

The T4127 option 2 (cumulative averaging), the commission employees
(TD1X), the change of province of employment during the year, and the indexation of a
TD1ON claim carried into a new year are not computed by this module.
