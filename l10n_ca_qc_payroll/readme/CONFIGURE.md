Payroll > Configuration > Settings > Quebec Payroll:

- enter the Revenu Québec identification number and the remittance
  frequency (monthly for a new employer);
- choose the Health Services Fund sector and the rate basis: total payroll
  of the previous year (enter it, associated employers included) or, for
  the first two years of contributions, the payroll paid since January 1;
  with that basis, keep the payroll of the associated employers paid since
  January 1 up to date each remittance period;
- with the previous-year basis, enter the previous-year payroll of the
  company alone subject to the WSDRF contribution (RL-1 summary line 51):
  the payslips accrue the WSDRF contribution only above its threshold;
- enter the CNESST rate per $100 of the classification decision of the
  year (leave 0 without CNESST coverage);
- check *Not Subject to the Labour Standards Contribution* only for the
  exempt employers (federal jurisdiction, charities, etc.).

Installing the module adds the Quebec rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts (employer contributions 512121, source deductions payable 221206).
The *Set Up Canadian Payroll* button does the same for a new company.

On each contract whose province of employment is Quebec, page *Canadian
Payroll*: the TP-1015.3 claim (basic personal amount, or lines 7 and 9 of
the form with the year of the form, line 7 being indexed on the pays of the
following years), the deductions of line 19, the amounts authorized on a
TP-1016, with the date they apply from when it falls after the first pay of
the year, the Fonds de solidarité FTQ and Fondaction withholdings per pay,
the additional Quebec tax per pay, the exemption from withholding and the
CNESST coverage.

RPP, RRSP, VRSP and PRPP contributions withheld per pay are entered on the
contract or in the *RPP Contribution* and *RRSP Contribution* inputs of the
payslip (Canadian federal payroll module): they lower both the federal and
the Quebec taxable income, and the RPP ones are reported in box D of the
RL-1. The other employee amounts that only TP-1015.F subtracts (FHSA, CIP
deduction; variable F) go in salary rules of category *Deduction Reducing
the Quebec Taxable Income*, with a sequence below 100.

Due dates skip the Quebec public holidays and the Revenu Québec closure
days when the *Canada - Tax Compliance Calendar* module is installed;
otherwise only Saturdays and Sundays move them.

Payroll > Configuration > Canadian Time Parameters: add a version when
Revenu Québec publishes the rates of a new year (TP-1015.F, usually in
December).

## Parameters and their sources

Every rate, ceiling, bracket table, credit amount and due date the Quebec
computation uses is a dated time parameter (Payroll > Configuration >
Canadian Time Parameters). A new year or a budget measure is a new version
of the parameter, dated from the day it applies. A parameter keeps its last
version until a later one replaces it, so a figure that does not change
between years has a single version. A payslip reads the version in force at
its pay date. The RL-1 slips and the RL-1 summary (RLZ-1.S) read the
version in force on December 31 of their year, and the RL-1 deadline reads
`l10n_ca.qc.rl1.due_month` in force on January 1 of the following year. The
remittance schedule reads the version in force on the last day of each
month (of the quarter or of the year for quarterly and annual remitters),
which also covers the twice-monthly and weekly periods of that month. The
tables below give the shipped versions, what the computation does with each
figure and the publication that sets it. Each parameter's record also
carries its source URLs in its description.

The federal parameters that apply to an employee working in Quebec belong to
`l10n_ca_payroll` and are documented there: the reduced EI rate
(`l10n_ca.ei.rate_qc`), the federal abatement (`l10n_ca.federal.qc_abatement`)
and the federal flat rate on a bonus in Quebec
(`l10n_ca.federal.bonus_flat_rate_qc`). The CPP rate of that module is also
used to convert the CPP withheld before a transfer to Quebec.

### Sources

- Revenu Québec, *Formulas to Calculate Source Deductions and Contributions*,
  TP-1015.F-V (2026-01):
  <https://www.revenuquebec.ca/documents/en/formulaires/tp/TP-1015.F-V(2026-01).pdf>.
  This publication sets the 2026 versions of the QPP, QPIP, Quebec income
  tax (brackets, basic personal amount, deduction for workers, indexation
  rate, labour-sponsored fund credit), lump-sum and Health Services Fund
  parameters. It also contains the worked examples of appendices 1 to 3.
- Revenu Québec, TP-1015.F-V (2025-01):
  <https://www.revenuquebec.ca/documents/en/formulaires/tp/TP-1015.F-V(2025-01).pdf>.
  This edition sets the same parameters for 2025.
- Revenu Québec, *Guide for Employers: Source Deductions and Contributions*,
  TP-1015.G-V (2026-01):
  <https://www.revenuquebec.ca/documents/en/formulaires/tp/TP-1015.G-V(2026-01).pdf>.
  It covers the QPP ages (parts 4.5.1 and 4.5.5), the indexation of the
  TP-1015.3 (part 3.4.1), the periodic HSF payments (part 6.5), the labour
  standards contribution (chapter 7) and the WSDRF (chapter 8). It also
  gives the remittance frequencies and due dates (part 11.3, table 7) and
  the CNESST periodic payments (part 11.8).
- Revenu Québec, *Guide to Filing the RL-1 Slip*, RL-1.G-V (2025-12):
  <https://www.revenuquebec.ca/documents/en/formulaires/rl/RL-1.G-V(2025-12).pdf>.
  It gives the filing deadline (section 4.2) and the cap of box G.
- Revenu Québec, *Guide du sommaire 1* (RLZ-1.S.G):
  <https://www.revenuquebec.ca/fr/services-en-ligne/formulaires-et-publications/rlz-1-s-g/guide-du-sommaire-1-sommaire-des-retenues-et-des-cotisations-de-lemployeur/>.
  It sets lines 61 to 64 (labour standards), lines 71 to 75 (WSDRF) and the
  filing deadlines after a cessation.
- Revenu Québec web pages:
  - QPP maximum pensionable earnings and contribution rate:
    <https://www.revenuquebec.ca/en/businesses/source-deductions-and-employer-contributions/calculating-source-deductions-and-contributions/qpp-contributions/maximum-pensionable-earnings-and-contribution-rate/>
  - QPIP maximum insurable earnings and premium rate:
    <https://www.revenuquebec.ca/en/businesses/source-deductions-and-employer-contributions/calculating-source-deductions-and-contributions/qpip-premiums/maximum-insurable-earnings-and-premium-rate/>
  - HSF total payroll threshold and contribution rates:
    <https://www.revenuquebec.ca/fr/entreprises/retenues-a-la-source-et-cotisations-de-lemployeur/calcul-des-retenues-et-des-cotisations/cotisation-de-lemployeur-fss/seuil-de-la-masse-salariale-totale-et-taux-de-cotisation-au-fss/>
  - WSDRF:
    <https://www.revenuquebec.ca/fr/entreprises/retenues-a-la-source-et-cotisations-de-lemployeur/calcul-des-retenues-et-des-cotisations/fonds-de-developpement-et-de-reconnaissance-des-competences-de-la-main-doeuvre/>
- Ministère des Finances du Québec, information bulletin 2025-8:
  <https://cdn-contenu.quebec.ca/cdn-contenu/adm/min/finances/publications-adm/Bulletins/FR/BULFR_2025-8.pdf>.
  It announces the 2026 cut of the QPP base rate and of the QPIP rates. It
  also announces a temporary 2026-2027 HSF exemption for some agriculture,
  forestry and fishing employers, which the module does not model.
- CNESST, *Salaire maximum annuel assurable*:
  <https://www.cnesst.gouv.qc.ca/fr/demarches-formulaires/employeurs/assurance-sante-securite-travail/tarification/annexes-tableaux/salaire-maximum-annuel-assurable>
  and
  <https://www.cnesst.gouv.qc.ca/fr/organisation/documentation/formulaires-publications/salaire-maximum-annuel-assurable>.
  It sets the maximum insurable earnings by rating year: 106,000 for 2027.
  *Déductions de base 2026* of the Gouvernement du Québec is a secondary
  source for the same amount:
  <https://cdn-contenu.quebec.ca/cdn-contenu/gouvernement/travailler/Services_employes_Etat/Remuneration/Deductions_base_2026.pdf>.
- Laws (LégisQuébec):
  - Act respecting the Québec Pension Plan, s. 44.1, 50 and 63:
    <https://www.legisquebec.gouv.qc.ca/en/document/cs/R-9>
  - Act respecting parental insurance, s. 78.1 (S.Q. 2025, c. 32):
    <https://www.legisquebec.gouv.qc.ca/en/document/cs/A-29.011>
  - Taxation Act, s. 358.0.1 (deduction for workers), 750 and 750.1
    (brackets and their indexation), 752.0.0.1 (personal credits) and 1015
    (remittances): <https://www.legisquebec.gouv.qc.ca/en/document/cs/I-3>
  - Act respecting the Régie de l'assurance maladie du Québec, s. 34 (HSF):
    <https://www.legisquebec.gouv.qc.ca/en/document/cs/R-5>
  - Act respecting labour standards, s. 39.0.1 and 39.0.2:
    <https://www.legisquebec.gouv.qc.ca/en/document/cs/N-1.1>
  - Act to promote workforce skills development and recognition, s. 3, s. 4
    and schedule: <https://www.legisquebec.gouv.qc.ca/en/document/cs/D-8.3>
  - Act respecting industrial accidents and occupational diseases, s. 66:
    <https://www.legisquebec.gouv.qc.ca/en/document/cs/A-3.001>
- CRA, *T4127 Payroll Deductions Formulas*, 122nd edition, effective January
  1, 2026. Its tables 8.3, 8.6 and 8.8 repeat the 2026 QPP and QPIP figures,
  and its K2Q gives the federal credit of the QPIP premium. Its URL is in the
  sources of `l10n_ca_payroll`.

### Quebec Pension Plan

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.qpp.ympe` | 71,300 | 74,600 | Maximum pensionable earnings (MPE): C maximum = (MPE - exemption) x rate. In C2, W = max(S5, MPE x PM/12). Caps RL-1 box G when box B.B is empty. | TP-1015.F-V part 3.1; RL-1.G-V box G |
| `l10n_ca.qpp.yampe` | 81,200 | 85,000 | Additional MPE: C2 maximum = (additional MPE - MPE) x rate2. Caps RL-1 box G when box B.B is filled. | TP-1015.F-V part 3.1; principal changes |
| `l10n_ca.qpp.basic_exemption` | 3,500 | 3,500 | C = rate x (S3 - 3,500 / P), the exemption per pay truncated to the cent. Also enters the C maximum. | TP-1015.F-V part 3.1 and its note |
| `l10n_ca.qpp.rate` | 6.40% | 6.30% | Rate of C (base + first additional). The employer pays the same amount. CS = C x (rate - base_rate) / rate + C2. | TP-1015.F-V part 3.1, part 3.2, principal changes; bulletin 2025-8 |
| `l10n_ca.qpp.base_rate` | 5.40% | 5.30% | Base part of the rate. The rest (1%) is the first additional contribution: CS = C x 0.01 / 0.0630 + C2 gives CSA and CSB of the Quebec tax, and F5 of the federal tax. | TP-1015.F-V part 2.1.1 (CS); bulletin 2025-8 |
| `l10n_ca.qpp.rate2` | 4% | 4% | C2 = min(max2 x PM/12 - A8, rate2 x (S5 + S3 - W)). The employer pays the same amount. | TP-1015.F-V part 3.1 |
| `l10n_ca.qpp.age_min` | 18 | 2025 version | PM starts the month after the 18th birthday. | TP-1015.G-V part 4.5.1; RL-1.G-V box G |
| `l10n_ca.qpp.last_contribution_age` | 72 | 2025 version | No QPP from January 1 of the year after the one in which the employee turns 72. The QPP has no stop at 70. | TP-1015.G-V part 4.5.5 |

Derived figures:

- Maximum employee contribution, also the employer maximum:
  - 2025: (71,300 - 3,500) x 6.40% = 67,800 x 0.064 = 4,339.20. This
    matches TP-1015.F-V (2025-01), principal changes.
  - 2026: (74,600 - 3,500) x 6.30% = 71,100 x 0.063 = 4,479.30. This
    matches TP-1015.F-V (2026-01) and T4127 table 8.3.
- Maximum second additional contribution:
  - 2025: (81,200 - 71,300) x 4% = 9,900 x 0.04 = 396.
  - 2026: (85,000 - 74,600) x 4% = 10,400 x 0.04 = 416. This matches
    TP-1015.F-V and T4127 table 8.6.
- Exemption per pay, 3,500 / P truncated to the cent: 291.66 (P = 12),
  145.83 (24), 134.61 (26) and 67.30 (52). The TP-1015.F-V note to part 3.1
  shows 67.30 for P = 52.
- Share of C deducted as CS: (rate - base_rate) / rate. This gives 0.01 /
  0.064 = 0.15625 in 2025 and 0.01 / 0.063 = 0.158730 in 2026, the C x
  (0,01 ÷ 0,0630) of TP-1015.F-V (2026-01).
- A QPP contribution above 0 but below 0.005 is withheld as 0.01
  (TP-1015.F-V note to part 3.1).
- CPP withheld this year before a transfer to Quebec counts against the QPP
  maximums. The code converts it by R x (QPP rate / CPP rate), which gives
  0.063 / 0.0595 = 1.0588235294 in 2026, the factor of TP-1015.G-V part
  4.5.9. For the second additional contribution it uses R2 x (4% / 4%).

### Quebec Parental Insurance Plan

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.qpip.mie` | 98,000 | 103,000 | Maximum insurable earnings: the employee maximum is MIE x rate and the employer maximum is MIE x employer rate. Caps RL-1 box I and T4 box 56. | TP-1015.F-V principal changes; parts 4.1 and 4.2 |
| `l10n_ca.qpip.rate` | 0.494% | 0.430% | Ap = min(maximum - A6, rate x S4), withheld as 0.01 when above 0 but below 0.005. Ap also enters the federal K2Q credit. | TP-1015.F-V part 4.1; Act respecting parental insurance s. 78.1 |
| `l10n_ca.qpip.employer_rate` | 0.692% | 0.602% | Ap1 = min(maximum - A7, rate x S4), rounded half up to the cent. RLZ-1.S line 29 = box I x rate. | TP-1015.F-V part 4.2 |

Derived figures:

- Maximum premiums:
  - 2025: 98,000 x 0.494% = 484.12 for the employee and 98,000 x 0.692% =
    678.16 for the employer. This matches TP-1015.F-V (2025-01).
  - 2026: 103,000 x 0.430% = 442.90 for the employee and 103,000 x 0.602% =
    620.06 for the employer. This matches TP-1015.F-V (2026-01) and T4127
    table 8.8. The federal K2Q of T4127 also uses 442.90 as its maximum.
- The employer rate is 1.4 times the employee rate: 0.430% x 1.4 = 0.602%.
  In 2025, 0.494% x 1.4 = 0.6916%, published rounded as 0.692%.
- The 2026 rates are the 2025 rates less 13%: 0.494% x 0.87 = 0.4298%,
  published as 0.430%, and 0.692% x 0.87 = 0.6020%.

### Quebec income tax

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.qc.brackets` | 14% to 53,255; 19% to 106,495; 24% to 129,590; 25.75% above | 14% to 54,345; 19% to 108,680; 24% to 132,245; 25.75% above | T is the rate of the bracket of the annual taxable income I, and K is derived from the table (truncated to the dollar). Y = T x I - K - K1 - 0.14 x E - 0.15 x P x Q - 0.15 x P x Q1. An income equal to a threshold stays in the lower bracket. | TP-1015.F-V part 2.1.1 step 2; principal changes |
| `l10n_ca.qc.credit_rate` | 14% | 14% | 0.14 x E in Y, where E = E1 + E2 rounded half up to the dollar. | TP-1015.F-V part 2.1.1 step 2 |
| `l10n_ca.qc.bpa` | 18,571 | 18,952 | E1 of an employee without a TP-1015.3. It is also the threshold of the flat rate on a lump-sum payment. | TP-1015.F-V part 2.1.1 (E1), part 2.1.2 note; principal changes |
| `l10n_ca.qc.indexation_rate` | none | 2.05% | E1 of a TP-1015.3 filed for an earlier year is multiplied by 1 + the rate of each later year up to the pay. Only a version dated in that year counts: a missing year stops the computation. | TP-1015.F-V (2026-01) principal changes and E1; TP-1015.G-V part 3.4.1 |
| `l10n_ca.qc.labour_fund_credit_rate` | none | 15% | 0.15 x P x Q (Fonds de solidarité FTQ) and 0.15 x P x Q1 (Fondaction) in Y, Q and Q1 being entered on the contract per pay. | TP-1015.F-V part 2.1.1 step 2, appendix 1 |
| `l10n_ca.qc.worker_deduction_rate` | 6% | 6% | H = min(0.06 x D, maximum / P), D being the salary of the pay without its lump sums, rounded to the cent. | TP-1015.F-V part 2.1.1 step 1 |
| `l10n_ca.qc.worker_deduction_max` | 1,420 | 1,450 | Annual maximum of H. The maximum per pay is this amount / P. | TP-1015.F-V part 2.1.1 step 1; principal changes |

Formulas: I = P x (G - F - H - CSA) - J - J1, with CSA = CS x (S3 - B2) /
S3. The tax of the pay is Y / P + L. The amounts F, J, J1, K1, E2, Q, Q1 and
L come from the salary rules and the contract, not from time parameters. J,
J1 and K1 entered from a date after the first pay of the year become P x
amount / PR.

Derived figures:

- Constant K of each bracket. K is the sum of threshold x (rate - previous
  rate), truncated to the dollar:
  - 2026: 54,345 x 0.05 = 2,717.25 -> 2,717; + 108,680 x 0.05 = 8,151.25 ->
    8,151; + 132,245 x 0.0175 = 10,465.5375 -> 10,465. These match the
    TP-1015.F-V (2026-01) table (0, 2,717, 8,151, 10,465).
  - 2025: 53,255 x 0.05 = 2,662.75 -> 2,662; + 106,495 x 0.05 = 7,987.50 ->
    7,987; + 129,590 x 0.0175 = 10,255.325 -> 10,255. These match the
    TP-1015.F-V (2025-01) table (0, 2,662, 7,987, 10,255).
- Credit of an employee without a TP-1015.3: 0.14 x 18,571 = 2,599.94 in
  2025 and 0.14 x 18,952 = 2,653.28 in 2026.
- Maximum deduction for workers per pay, the maximum / P rounded to the
  cent:
  - 2025: 118.33 (P = 12), 59.17 (24), 54.62 (26) and 27.31 (52).
  - 2026: 120.83 (P = 12), 60.42 (24), 55.77 (26) and 27.88 (52).
    TP-1015.F-V (2026-01) appendices 1 and 2 use 55.77 and 27.88.
- Indexation of a TP-1015.3 of 2025 on a 2026 pay: E1 x 1.0205, the
  factor stated in TP-1015.F-V (2026-01), variable E1.

### Lump-sum payments

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.qc.lump_sum_flat_rate` | 7% | 2025 version | Tax on a bonus, retroactive payment or similar lump sum when P x salary + the lump sums of the year (B1 + B2) total at most `l10n_ca.qc.bpa`. Otherwise the second method applies: A = T x (B2 - CSB), T being the bracket rate of I = P x (G - F - H - CSA) + B1 + B2 - CSB1 - CSB - J - J1. | TP-1015.F-V part 2.1.2, note and second method |

Derived figures:

- Flat-rate threshold: 18,571 in 2025 and 18,952 in 2026, the basic personal
  amount. This matches the "Gratuities and retroactive pay" principal
  change of each edition.
- CSB = CS x B2 / S3, the share of the additional QPP contributions on the
  lump sum, rounded to the cent. CSB1 is the year-to-date total of CSB.

### Employer contributions

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.qc.hsf.formula` | general 1.2662 + 0.3838 x S; primary and manufacturing 0.8074 + 0.4426 x S; public 4.26 | same | HSF rate W in percent, W = a + b x S for the sector of the company, rounded half up to two decimals. HSF of the pay = W% x S2. RLZ-1.S line 54 recomputes W on the actual total payroll (line 50.1). | TP-1015.F-V part 5; TP-1015.G-V part 6.5 (rate shown to two decimals, e.g. 1.48% at 1,511,420); HSF rates page |
| `l10n_ca.qc.hsf.payroll_min` | 1,000,000 | 1,000,000 | Lower bound of the total payroll: S = max(payroll, 1,000,000) / 1,000,000. | TP-1015.F-V part 5 |
| `l10n_ca.qc.hsf.payroll_max` | 7,800,000 | 7,800,000 | Upper bound of the total payroll: S is at most 7.8. | TP-1015.F-V part 5; principal changes |
| `l10n_ca.qc.cnt.rate` | 0.06% | 0.06% | Labour standards contribution of the pay = rate x min(gross, maximum - Quebec salary of the year). RLZ-1.S line 63 = line 61 x rate. | TP-1015.G-V chapter 7; RLZ-1.S.G |
| `l10n_ca.qc.cnt.max_remuneration` | 98,000 | 103,000 | Remuneration subject to the contribution, per employee and year (the QPIP maximum insurable earnings). It caps the RL-1 base `cnt_base`. | TP-1015.G-V chapter 7 |
| `l10n_ca.qc.wsdrf.rate` | 1% | 1% | When the company's own payroll subject to the WSDRF exceeds the threshold, each pay accrues rate x gross. RLZ-1.S line 73 = line 71 x rate, and line 75 (the WSDRF contribution) = line 73 less the training expenditures used (line 74). | TP-1015.G-V chapter 8; RLZ-1.S.G lines 71 to 75 |
| `l10n_ca.qc.wsdrf.payroll_threshold` | 2,000,000 | 2,000,000 | The participation applies only above this payroll, which is the previous-year estimate or, for a new employer, the year to date. | TP-1015.G-V chapter 8; RLZ-1.S.G line 71 |
| `l10n_ca.qc.cnesst.max_insurable` | 98,000 | 103,000; 106,000 from 2027 | CNESST premium of the pay = company rate per $100 x min(gross, maximum - Quebec salary of the year) / 100. The rate per $100 is a company field set by the CNESST classification decision. | CNESST maximum insurable earnings page; TP-1015.G-V part 11.8 |

Derived figures:

- Minimum HSF rates (S = 1): 1.2662 + 0.3838 = 1.65% (general) and 0.8074 +
  0.4426 = 1.25% (primary and manufacturing).
- Maximum HSF rates (S = 7.8): 1.2662 + 0.3838 x 7.8 = 4.25984 -> 4.26%,
  and 0.8074 + 0.4426 x 7.8 = 4.25968 -> 4.26%. Both equal the public
  sector rate, as in the TP-1015.F-V table.
- A primary and manufacturing employer with a total payroll of 2,000,000:
  0.8074 + 0.4426 x 2 = 1.6926 -> 1.69%. This is the rate of the example of
  TP-1015.G-V part 6.6.2.
- Maximum labour standards contribution per employee: 98,000 x 0.06% =
  58.80 in 2025 and 103,000 x 0.06% = 61.80 in 2026.

### Remittances and RL-1

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.qc.rl1.due_month` | 2 | 2025 version | The RL-1 slips, the RLZ-1.S and the labour standards and WSDRF balances are due on the last day of this month of the following year. The deadline is earlier after a cessation (30 days later) or after a last periodic remittance (the 20th of the next month). | RL-1.G-V section 4.2; RLZ-1.S.G |
| `l10n_ca.qc.remittance.due_day` | 15 | 2025 version | Monthly, quarterly and annual remittances are due on this day of the month after the period. | TP-1015.G-V table 7 |
| `l10n_ca.qc.remittance.twice_monthly_split_day` | 15 | 2025 version | Last day of the first twice-monthly period (remuneration paid before the 16th). | TP-1015.G-V table 7 |
| `l10n_ca.qc.remittance.twice_monthly_first_due_day` | 25 | 2025 version | Due day, in the same month, of the first twice-monthly period. | TP-1015.G-V table 7 |
| `l10n_ca.qc.remittance.twice_monthly_second_due_day` | 10 | 2025 version | Due day, in the following month, of the second twice-monthly period. | TP-1015.G-V table 7 |
| `l10n_ca.qc.remittance.weekly_period_end_days` | 7, 14, 21 | 2025 version | Last days of the first three weekly periods. The fourth period ends on the last day of the month. | TP-1015.G-V table 7 |
| `l10n_ca.qc.remittance.weekly_working_days` | 3 | 2025 version | A weekly remittance is due this many business days after the end of its period. | TP-1015.G-V table 7 |

Every due date that falls on a Saturday, a Sunday, a Quebec public holiday or
a Revenu Québec closure day moves to the next business day (TP-1015.G-V part
11.3). The holidays and closure days come from the Tax Compliance Calendar
module when it is installed; they are not time parameters.

### Worked examples

The tests of the module assert the following amounts with the shipped
parameters. Unless stated otherwise, each pay is monthly (P = 12), in 2026,
with the basic personal amount as E. The federal tax is computed by
`l10n_ca_payroll` and appears only as a result.

- **K constants**: K from the shipped brackets is 0, 2,717, 8,151 and
  10,465 for 2026, and 2,662, 7,987 and 10,255 for 2025. These are the
  TP-1015.F-V tables. Test: `test_quebec_bracket_constants`.
- **HSF rate selection** (general sector): 1.65% up to 1,000,000; 2.03% at
  2,000,000 (2.0338); 4.26% from 7,800,000. Primary and manufacturing:
  1.69% at 2,000,000, the TP-1015.G-V part 6.6.2 example, and 1.25% at
  500,000. Public: 4.26%. Test: `test_hsf_rate_selection`.
- **Monthly salary of 5,000**:
  - QPP: C = 0.063 x (5,000 - 291.66) = 296.63.
  - QPIP: 21.50 for the employee and 30.10 for the employer.
  - Quebec tax: H = min(300, 120.83) = 120.83, CSA = 296.63 / 6.3 = 47.08
    and I = 12 x (5,000 - 120.83 - 47.08) = 57,985.08, so T = 19% and K =
    2,717. Y = 11,017.17 - 2,717 - 2,653.28 = 5,646.89, and the tax of the
    pay is 470.57.
  - Employer: HSF 1.65% x 5,000 = 82.50 and CNT 3.00.
  - Federal tax: 368.94 (EI 65.00).

  Test: `test_monthly_5000`.
- **Bi-weekly pay of 3,000** (P = 26):
  - QPP: C = 0.063 x (3,000 - 134.61) = 180.52.
  - QPIP: 12.90 for the employee and 18.06 for the employer.
  - Quebec tax: H = 55.77, CSA = 28.65 and I = 75,805.08, so Y = 9,032.69
    and the tax of the pay is 347.41.
  - Employer: HSF 49.50 and CNT 1.80.

  Test: `test_biweekly_3000`.
- **TP-1015.3 with E = 0 and additional tax**: on the 5,000 pay, Y =
  8,300.17 gives 691.68, and 25.00 of additional tax brings the total to
  716.68. With the exemption from withholding, the Quebec tax is 0 and the
  federal tax stays 368.94. Test: `test_claim_additional_tax_and_exemption`.
- **Indexation of a TP-1015.3**: line 7 = 20,000 on a form of 2026 gives a
  tax of 458.35. The same amount on a form of 2025 becomes E1 = 20,000 x
  1.0205 = 20,410, which gives 453.56. A form of 2024 is refused, because no
  2025 indexation rate is shipped. Test: `test_claim_indexation`.
- **TP-1015.F-V appendix 1** (regular payments): 4,000 every two weeks, an
  RPP contribution of 200 per pay (F), E = 21,830, Q = 100 and Q1 = 150.
  - C = 243.52, CSA = 38.65 and H = 55.77, so I = 26 x 3,705.58 =
    96,345.08.
  - Y = 18,305.57 - 2,717 - 3,056.20 - 390 - 585 = 11,557.37.
  - The tax of the pay is 444.51, the amount of the appendix for the first
    18 pays.

  The RPP contribution is the amount per pay of the contract, which also
  gives box D of the RL-1 (200). Test: `test_example_appendix_1`.
- **Deduction for Quebec only**: 5,000 a month with an FHSA contribution of
  100 in category *Deduction Reducing the Quebec Taxable Income*. The
  federal tax stays 368.94; I = 12 x (5,000 - 100 - 120.83 - 47.08) =
  56,785.08 and Y = 0.19 x 56,785.08 - 2,717 - 2,653.28 = 5,418.89, so the
  Quebec tax is 451.57. Test: `test_quebec_only_deduction`.
- **TP-1015.F-V appendix 2** (retroactive payment, second method): 1,500 a
  week (P = 52) with an RPP contribution of 100, and a retroactive payment
  of 4,000 of which 400 go to the RPP.
  - C = 0.063 x (5,500 - 67.30) = 342.26 and CS = 54.327, so CSA = 14.82,
    CSB = 39.51 and H = 27.88.
  - I = 70,579.60 + 3,600 - 39.51 = 74,140.09, so T = 19% and A = 0.19 x
    (3,600 - 39.51) = 676.49, as in the appendix.
  - The regular part of the same pay is 154.61, computed with CSA = 14.82.
    The appendix states 154.89 as the employer's usual withholding on the
    salary, a given of the example, not a result of the formula.

  Test: `test_example_appendix_2`.
- **Flat rate on a lump sum**: salary of 1,000 and a bonus of 2,000 in
  March. 12,000 + 2,000 = 14,000 is at most 18,952, so the tax is 7% x
  2,000 = 140.00. In April, a bonus of 5,000 brings the total to 19,000,
  which is above 18,952, so the second method applies.
  - CSB = 47.57 and CSB1 = 18.06, so I = 18,100.25 and T = 14%.
  - A = 0.14 x (5,000 - 47.57) = 693.34.

  Test: `test_lump_sum_flat_rate`.
- **Bonus in the RL-1 boxes**: 5,000 + a bonus of 1,000 gives C = 0.063 x
  (6,000 - 291.66) = 359.63 and QPIP 25.80. RL-1 boxes A, G and I are
  6,000. Test: `test_bonus_counts_in_rl1_box_a`.
- **TP-1016 amounts from July 1**: J1 = 6,000 and K1 = 600 apply from the
  seventh pay. PR = 6, so J1 = 12 x 6,000 / 6 = 12,000 and K1 = 1,200.
  I = 45,985.08 falls in the 14% bracket, Y = 2,584.63 and the tax of the
  pay is 215.39. The earlier pays keep 470.57. Test:
  `test_amounts_from_a_later_date`.
- **Minimum of one cent**: C = 0.063 x (291.70 - 291.66) = 0.00252 is
  withheld as 0.01. QPIP 0.0043 x 0.50 = 0.00215 is withheld as 0.01, and
  the employer premium 0.00301 rounds to 0.00. Test:
  `test_minimum_contribution_of_one_cent`.
- **Low income**: on 1,500, C = 76.13, H = 90 and CSA = 12.08, so I =
  16,775.04. 0.14 x I = 2,348.51 is below 2,653.28, so the Quebec tax is 0.
  Test: `test_low_income_no_quebec_tax`.
- **HSF above the minimum, CNESST and WSDRF**: a previous-year total payroll
  of 2,500,000 gives 1.2662 + 0.3838 x 2.5 = 2.2257 -> 2.23%, so the HSF on
  5,000 is 111.50. A CNESST rate of 1.25 per $100 gives 62.50. No WSDRF
  accrues while the company's own payroll (1,500,000) is below 2,000,000.
  At 2,100,000 it accrues 1% x 5,000 = 50.00. Test:
  `test_employer_rates_cnesst_wsdrf`.
- **HSF of a new employer**: with a payroll to date of 5,000, the rate is
  1.65% (82.50). With 2,000,000 of associated payroll, S = 2.005 gives
  2.0357 -> 2.04% (102.00). Test: `test_hsf_year_to_date_basis`.
- **HSF per remittance period** (primary and manufacturing, monthly
  remitter): a pay of 525,000 is accrued at 1.25%. The March payroll of
  1,050,000 gives 0.8074 + 0.4426 x 1.05 = 1.27213 -> 1.27%, and the March
  remittance carries 1.27% x 1,050,000 = 13,335.00. Test:
  `test_hsf_year_to_date_remittance_period`.
- **QPP ages**:
  - An employee who turns 72 in 2026 contributes all year (296.63 in
    November). One who turns 73 has no QPP from January 1. Test:
    `test_qpp_until_the_year_of_72`.
  - An employee born on March 10, 2008 contributes from April 2026. Test:
    `test_qpp_starts_after_18`.
- **Maximums, RL-1, T4 and remittances**: 15,000 a month for eight months.
  - QPP: 926.63 a month for four months, then 4,479.30 - 4 x 926.63 =
    772.78.
  - QPP2: (60,000 + 15,000 - 74,600) x 4% = 16.00 in May, then 416 - 16 =
    400 in June.
  - QPIP: 64.50 a month, then 442.90 - 387 = 55.90 in July. The employer
    premium is 90.30, then 620.06 - 541.80 = 78.26.
  - CNT: 9.00 a month, then (103,000 - 90,000) x 0.06% = 7.80, then 0.
  - Quebec tax: I = 176,785.08 is in the 25.75% bracket with K = 10,465,
    so the tax is 2,700.32 for months 1 to 4, then 2,702.49 in month 5,
    2,635.20 in month 6 and 2,738.20 in months 7 and 8.
  - RL-1: box B.A 4,479.30, B.B 416, G 85,000 (capped at the additional MPE
    because B.B is filled), H 442.90 and I 103,000.
  - T4: boxes 55 and 56 are 442.90 and 103,000.
  - RLZ-1.S: line 25 = 2 x (4,479.30 + 416) = 9,790.60, line 29 = 103,000 x
    0.602% = 620.06, line 54 = 1.65%, line 55 = 1,980.00 and line 63 =
    103,000 x 0.06% = 61.80.
  - The January remittance is due February 16, 2026, because the 15th is a
    Sunday. The RL-1 is due March 1, 2027, because February 28, 2027 is a
    Sunday.

  Test: `test_maximums_rl1_t4_and_remittances`.
- **Remittance periods of 2026**:
  - Annual: due January 15, 2027.
  - Quarterly: the second quarter is due July 15.
  - Twice-monthly: January 1-15 is due January 26 (the 25th is a Sunday),
    and January 16-31 is due February 10.
  - Weekly: January 1-7 is due on the third business day, January 12.

  Test: `test_remittance_periods`.
- **Closure days**: with the year-end closure days, the last weekly period
  of 2026 is due January 7, 2027 and the twice-monthly December 1-15 period
  is due December 29. The RL-1 deadline after a last remittance on August
  10 is September 21 (the 20th is a Sunday). After a cessation on June 15,
  it is July 15. Test: `test_due_dates_skip_closure_days`.

### Updating for a new year

- Read the new TP-1015.F-V. Its edition is dated January of the year
  (e.g. 2026-01) and includes the measures announced up to late November
  of the previous year (November 25, 2025 for the 2026 edition). Check
  Revenu Québec's site for later changes. Its "principal changes" pages
  list the year's figures for the income tax, QPP, QPIP and HSF formulas.
  Then read the TP-1015.G-V of the same edition for the employer
  contributions and the RL-1.G-V for the slips.
- Indexed or recomputed every year, so expect a new version each January
  1:
  - the bracket thresholds of `l10n_ca.qc.brackets`; K follows, so check
    it against the published table with `test_quebec_bracket_constants`;
  - `l10n_ca.qc.bpa`, which also sets the lump-sum flat-rate threshold;
  - `l10n_ca.qc.worker_deduction_max`;
  - `l10n_ca.qc.indexation_rate`, which must have a version dated in the
    year itself, or a TP-1015.3 of an earlier year cannot be indexed;
  - the QPP `ympe` and `yampe`;
  - the QPIP `mie`, with `l10n_ca.qc.cnt.max_remuneration` set to the same
    amount;
  - `l10n_ca.qc.cnesst.max_insurable`, which the CNESST publishes in the
    fall for the next rating year (106,000 for 2027). The QPIP maximum and
    the CNT maximum follow the same amount by law, but get their version
    only once the QPIP and Revenu Québec publish it.
- Changed only by a budget, a law or a regulation:
  - the QPP rates (`rate`, `base_rate`, `rate2`) and `basic_exemption`.
    The 2026 base rate is a one-year cut. Bulletin 2025-8 states that the
    s. 44.1 rule applies again, as written, for 2027. Check the 2027 rates
    in TP-1015.F-V (2027-01) and add a version only if they differ from
    5.30% / 6.30%;
  - the QPIP rates;
  - the credit rate, the labour-sponsored fund credit rate, the lump-sum
    flat rate and the deduction for workers rate;
  - the HSF formula and its payroll bounds;
  - the CNT and WSDRF rates and the WSDRF threshold;
  - the QPP ages;
  - the RL-1 month and the remittance days.
- A figure that does not change needs no new version: the last version
  stays in force.
