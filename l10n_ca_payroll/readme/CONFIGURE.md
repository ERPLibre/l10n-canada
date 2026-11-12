Payroll > Configuration > Settings > Canadian Payroll:

- enter the payroll program account (RP) and the remitter type assigned by
  the CRA;
- enter the reduced EI employer multiplier if the company takes part in
  the EI Premium Reduction Program;
- click *Set Up Canadian Payroll*: the company gets the *Canada - Base*
  structure as default and, with the `ca_2023` chart, the salary rules get
  their accounts (salaries 512110, employer contributions 512121, wages
  payable 221203, source deductions and the RPP, RRSP, union dues and
  support payments withheld, 221206). Accounts already set are kept;
  change them on each salary rule.

On each contract, page *Canadian Payroll*: province of employment, pay
periods per year (computed from the scheduled pay, "Bi-monthly" meaning
twice a month), federal TD1 claim, additional tax, RPP and RRSP
contributions, union dues and support payments withheld per pay,
exemptions. A support order that caps the payment at a percentage of the
net salary needs the amount after that cap (T4127, F2), and F2 applies
only to an order dated before May 1, 1997 that a CRA tax services office
authorized. Check *Union Issues Receipts* when the union gives its own
receipts: the dues still lower the withholding, but box 44 of the T4 (and
box F of the RL-1) stays empty. The wage of
the contract is monthly; the basic salary of a pay is wage * 12 / pay
periods. Set the birth date of the employee for the CPP age limits, and
the identification number for the SIN printed on the T4.

The salary journal of the contract receives the payroll entries.

Payroll > Configuration > Canadian Time Parameters: add a version when the
CRA publishes new rates (the YMPE and YAMPE are published in the fall, the
indexed federal brackets with the January edition of T4127).

## Parameters and their sources

The official sources are also records: Payroll > Configuration > Canadian
Official Sources lists each publication, page and statute, the time
parameters whose description cites it, and whether it was verified or is
still to confirm in a browser, with the note that says what to check. The
page `static/description/sources.html` shows the same records; regenerate it
with `python3 l10n_ca_payroll/tools/sources_page.py <module>` after changing
`data/l10n_ca_payroll_source_data.xml`, as a test checks it is up to date.

A weekly scheduled action, *Canadian Payroll: Check the Official Sources*,
reads the pages of the sources that have a watcher, for the current and
the next year, and compares the figures found with the time parameters in
force on January 1 of that year. It never writes a parameter. A source
shows *Up to date*, *Next year not yet published*, *Published, not in the
parameters* (enter the new version), *Differs from the parameters*, *Page
unreachable* or *Page changed*: the page no longer has the table or the
row the watcher reads, which usually means it moved or was redesigned, so
check the page and the watcher. The last four states post the result on
the source and give a payroll manager a to-do activity, once per finding.
A watcher that only detects a publication (the January T4127, the PDF
guides of Revenu Québec) stays at *Published* until a manager clicks *Mark
Next Year Reviewed*. *Check Now* runs the check of one source. The federal
watchers read the CRA tables of the CPP, CPP2 and EI, its indexation page
and the list of T4127 editions.

Every rate, ceiling, bracket table, credit amount and due date the module
computes with is a dated time parameter (Payroll > Configuration > Canadian
Time Parameters). A version applies from its date until the next version of
the same parameter. A new year or a budget is a new version, never a change
to the code. The tables below give the shipped versions, what the
computation does with each figure and the publication that sets it. In the
tables, "—" means that the parameter has no version of that date and the
previous one stays in force. The description of each parameter record gives
its sources with their URLs.

### Sources

- **CRA T4127, Payroll Deductions Formulas, 122nd edition, effective
  January 1, 2026** —
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jan/t4127-jan-payroll-deductions-formulas-computer-programs.html>.
  Chapter 2 (BPAF formula), chapter 4 (option 1 formulas, bonus formulas
  and their example), chapter 6 (CPP, table 6.1), chapter 7 (EI),
  chapter 8: tables 8.1 to 8.9 for 2026 and tables 8.22 to 8.28 for 2025.
  Sets the 2026 federal tax, CPP and EI figures, the 2025 CPP and EI
  figures, the bonus flat rates and the CPP age limits.
- **CRA T4127, 120th edition, effective January 1, 2025** —
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/payroll-deductions-t4127-payroll-deductions-formulas/t4127-jan-120th-edition-effective-january-1-2025/t4127-jan-payroll-deductions-formulas-computer-programs.html>.
  Table 8.1 for 2025 with the lowest rate of 15% (constants 0, 3,156,
  9,467, 14,803, 24,940) and the credit rate of 15% to June 30, 2025. For
  the 2025 tax year, the Income Tax Act as amended by S.C. 2026, c. 2 sets
  a single rate of 14.5%; the payroll withholds 15% then 14%, and the
  return of the employee reconciles the difference.
- **CRA T4127, 121st edition, effective July 1, 2025** (French) —
  <https://www.canada.ca/fr/agence-revenu/services/formulaires-publications/retenues-paie/t4127-formules-calcul-retenues-paie-annees-precedentes/t4127-jul-121e-edition-vigueur-1er-juillet-2025/t4127-jul-formules-calcul-retenues-paie.html>.
  Tables 8.1 and 8.2 for 2025 with the lowest rate of 14% from July 1, 2025;
  K1 with the 2025 basic personal amount. Sets the 2025 federal brackets,
  credit rate, basic personal amounts and Canada employment amount.
- **CRA, CPP contribution rates, maximums and exemptions** —
  <https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/canada-pension-plan-cpp/cpp-contribution-rates-maximums-exemptions.html>.
  YMPE, YAMPE, basic exemption, CPP and CPP2 rates; the 2027 rows (YMPE
  76,700, YAMPE 87,400, rate 5.75%, maximum 4,209.00, maximum CPP2
  428.00) set the 2027 versions of the YMPE and YAMPE.
- **CRA, EI premium rates and maximums** —
  <https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/employment-insurance-ei/ei-premium-rates-maximums.html>.
  EI maximum insurable earnings and rates.
- **ESDC, Canada Employment Insurance Commission confirms the 2027
  employment insurance premium rate (news release, September 2026)** —
  <https://www.canada.ca/en/employment-social-development/news/2026/09/canada-employment-insurance-commission-confirms-2027-employment-insurance-premium-rate.html>,
  with the 2027 premium rate report
  <https://www.canada.ca/en/employment-social-development/programs/ei/ei-list/reports/premium/rates2027.html>.
  2027 maximum insurable earnings (70,800) and rates (1.64%, 1.29% in
  Quebec).
- **Spring Economic Update 2026 Implementation Act, S.C. 2026, c. 22
  (Bill C-30)** — Department of Finance news release
  <https://www.canada.ca/en/department-finance/news/2026/06/legislation-passes-to-implement-measures-from-the-spring-economic-update-2026.html>
  and LEGISinfo <https://www.parl.ca/legisinfo/en/bill/45-1/C-30>. The base
  CPP rate goes from 9.9% to 9.5% (employee and employer combined) from
  2027: the 2027 versions of the CPP rates.
- **CRA T4001, Employers' Guide – Payroll Deductions and Remittances** —
  <https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4001/employers-guide-payroll-deductions-remittances.html>.
  "Remittance due dates" (due days of each remitter type, next business day
  for a weekend or a public holiday) and "Filing information returns" (T4
  due on the last day of February of the following year).
- **CRA, T4 Summary** —
  <https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/completing-filing-information-returns/t4-information-employers/t4-summary.html>.
  Lines of the T4 Summary.
- **Laws and regulations** cited by the parameter records:
  - Income Tax Act <https://laws-lois.justice.gc.ca/eng/acts/I-3.3/>:
    s. 117(2) (rates), s. 117.1 (indexing), s. 118 and 118(1)(c) (basic
    personal amount), s. 118(10) (Canada employment amount), s. 120(2)
    (Quebec abatement).
  - Federal-Provincial Fiscal Arrangements Act, s. 27
    <https://laws-lois.justice.gc.ca/eng/acts/F-8/> (Quebec abatement).
  - Canada Pension Plan: s. 8 and Schedules 1 and 2 (rates), s. 12(1) (age
    limits), s. 18 (YMPE), s. 18.1 (YAMPE), s. 19-20 (basic exemption).
  - Employment Insurance Act <https://laws-lois.justice.gc.ca/eng/acts/E-5.6/>:
    s. 4 (maximum insurable earnings), s. 66 (rate), s. 68 (employer
    premium), s. 69 (reduced rate of Quebec).
  - Income Tax Regulations, C.R.C., c. 945
    <https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._945/>:
    s. 108(1) and 108(1.1)(a) and (b) (remittance due dates), s. 205(1)
    (T4 filing deadline).
- **Revenu Québec TP-1015.F, 2026**, part 3.1: QPP of an employee
  transferred from a CPP establishment. No parameter of this module comes
  from it; one worked example reproduces its formula.

### Federal income tax

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.federal.brackets` | Jan 1: 15% to 57,375; 20.5% to 114,750; 26% to 177,882; 29% to 253,414; 33% above. Jul 1: same thresholds, 14% for the first bracket | 14% to 58,523; 20.5% to 117,045; 26% to 181,440; 29% to 258,482; 33% above | R of step 2 is the rate of the bracket that contains A; K is derived from the table (see below). T3 = R × A − K − K1 − K2 − K3 − K4 | T4127 122nd ed. table 8.1 (2026); 121st ed. table 8.1 (July 2025); ITA s. 117(2), 117.1 |
| `l10n_ca.federal.credit_rate` | 0.15 → 15% to June 30, 0.14 → 14% from July 1 | 0.14 → 14% | Multiplies the credits: K1 = rate × TC, K2 = rate × (CPP base + EI), K4 = rate × min(employment income, CEA) | T4127 122nd ed. ch. 4 step 2 (K1, K2, K4); 120th ed. ch. 4 (15%); 121st ed. ch. 4 (14%); ITA s. 117(2), 118 |
| `l10n_ca.federal.bpa_max` | 16,129 | 16,452 | BPAF when NI ≤ phase-out start; TC of a contract that claims the basic personal amount; shown on the contract | T4127 122nd ed. ch. 2 (BPAF formula), table 8.9; 121st ed. ch. 4 (K1 = 0.14 × 16,129); ITA s. 118(1)(c) |
| `l10n_ca.federal.bpa_min` | 14,538 | 14,829 | BPAF when NI ≥ phase-out end | T4127 122nd ed. ch. 2 (BPAF formula); 121st ed. ch. 2 (claim codes); ITA s. 118(1)(c) |
| `l10n_ca.federal.bpa_phaseout_start` | 177,882 | 181,440 | Start of the linear decrease of BPAF; NI = A + HD in T4127, and the module has no HD, so NI is the annual taxable income A | T4127 122nd ed. ch. 2 (BPAF formula), table 8.1 (4th threshold); 121st ed. table 8.1 |
| `l10n_ca.federal.bpa_phaseout_end` | 253,414 | 258,482 | End of the decrease of BPAF | T4127 122nd ed. ch. 2 (BPAF formula), table 8.1 (5th threshold); 121st ed. table 8.1 |
| `l10n_ca.federal.canada_employment_amount` | 1,471 | 1,501 | CEA of K4 = min(rate × annual employment income, rate × CEA); employment income is P × regular gross plus the non-periodic payments of the year | T4127 122nd ed. table 8.2 (2026), table 8.23 (2025); ITA s. 118(10) |
| `l10n_ca.federal.qc_abatement` | 0.165 → 16.5% | 0.165 → 16.5% | Employment in Quebec only: T1 = T3 − 0.165 × T3 (step 3) | T4127 122nd ed. ch. 4 step 3, table 8.2; 121st ed. table 8.2; ITA s. 120(2) |

Derived figures:

- **Bracket constants K.** The code computes K = R × A − tax(A) for the
  bracket that contains A, which equals the running sum
  K(i) = K(i−1) + (R(i) − R(i−1)) × threshold(i), and rounds it to the
  dollar (half up).
  - 2026: 0.065 × 58,523 = 3,803.995 → **3,804**; + 0.055 × 117,045
    = 10,241.47 → **10,241**; + 0.03 × 181,440 = 15,684.67 → **15,685**;
    + 0.04 × 258,482 = 26,023.95 → **26,024**. Matches T4127 122nd ed.
    table 8.1 (0, 3,804, 10,241, 15,685, 26,024).
  - 2025 from July 1 (14%): 0.065 × 57,375 = 3,729.375 → **3,729**;
    + 0.055 × 114,750 = 10,040.625 → **10,041**; + 0.03 × 177,882
    = 15,377.085 → **15,377**; + 0.04 × 253,414 = 25,513.645 → **25,514**.
    Matches T4127 121st ed. table 8.1 (0, 3,729, 10,041, 15,377, 25,514).
  - 2025 to June 30 (15%): 0.055 × 57,375 = 3,155.625 → **3,156**;
    + 6,311.25 = 9,466.875 → **9,467**; + 5,336.46 = 14,803.335
    → **14,803**; + 10,136.56 = 24,939.895 → **24,940**. Matches T4127
    120th ed. table 8.1 (0, 3,156, 9,467, 14,803, 24,940). The 2025 table
    8.22 of the 122nd edition gives the constants of the 14.5% rate for the
    whole year (3,443, 9,754, 15,090, 25,227), not these.
- **Phase-out of BPAF.** BPAF = max − (NI − start) × (max − min) /
  (end − start), rounded to the cent. 2026: 1,623 / 77,042, as in the
  T4127 122nd ed. BPAF formula. 2025: 1,591 / 75,532.
- **K1 at the maximum basic personal amount.** 2026: 0.14 × 16,452
  = 2,303.28 (T4127 122nd ed. ch. 4 bonus example). 2025: 0.15 × 16,129
  = 2,419.35 to June 30, 0.14 × 16,129 = 2,258.06 from July 1.
- **K4 at the maximum.** 2026: 0.14 × 1,501 = 210.14 (T4127 122nd ed.
  ch. 4 bonus example). 2025: 0.15 × 1,471 = 220.65 to June 30,
  0.14 × 1,471 = 205.94 from July 1.
- **Maximum K2 outside Quebec** (maximum base CPP + maximum EI premium,
  see the tables below). 2026: 0.14 × (3,519.45 + 1,123.07) = 649.95.
  2025: 0.15 × (3,356.10 + 1,077.48) = 665.04 to June 30, 0.14 × 4,433.58
  = 620.70 from July 1. Once a maximum is reached in the year, K2 keeps
  the maximum for the rest of the year.
- **Quebec.** T1 = 0.835 × T3.

### Bonuses and other non-periodic payments

| Parameter | 2025 | 2026 | What the computation does with it | Source |
|---|---|---|---|---|
| `l10n_ca.federal.bonus_flat_threshold` | 5,000 | — | When A with the payment, P × (I − F5A) + (B − F3 − F5B) + (B1 − F5BYTD), is at most this amount, TB is the flat rate instead of the difference of T1 with and without the payment | T4127 122nd ed. ch. 4, bonus formulas, step 1 note; 121st ed. same note |
| `l10n_ca.federal.bonus_flat_rate` | 0.15 → 15% | — | TB = 15% × (B − F3) outside Quebec | Same note: "deduct 15% tax (10% in Quebec)" |
| `l10n_ca.federal.bonus_flat_rate_qc` | 0.10 → 10% | — | TB = 10% × (B − F3) for an employment in Quebec | Same note |

Derived figures:

- B is the total of the rules of category *Bonuses and Lump-Sum Payments*
  (`CA_LUMP`), F3 the deductions of category *Deduction From a Bonus or
  Lump-Sum Payment* (`CA_LUMP_DED`), B1 and F5BYTD the year-to-date totals
  of rules `CA_NPP` and `CA_F5B`.
- F5 = C × (rate − base rate) / rate + C2: the factor 0.0100 / 0.0595 of
  T4127 F5 comes from `l10n_ca.cpp.rate` − `l10n_ca.cpp.base_rate` over
  `l10n_ca.cpp.rate`. F5A = F5 × (PI − B) / PI, F5B = F5 × B / PI.
- Above the threshold, K2 of step 1 annualizes the regular contributions
  and adds once the contributions withheld on the payment, as in the T4127
  example.

### Canada Pension Plan

| Parameter | 2025 | 2026 | 2027 | What the computation does with it | Source |
|---|---|---|---|---|---|
| `l10n_ca.cpp.ympe` | 71,300 | 74,600 | 76,700 | Maximum C = (YMPE − exemption) × rate; CPP2 starts at W = max(PIYTD, YMPE × PM/12) | T4127 122nd ed. table 8.3 (2026), 8.24 (2025); CRA CPP rates page (2027); CPP s. 18 |
| `l10n_ca.cpp.yampe` | 81,200 | 85,000 | 87,400 | Maximum C2 = (YAMPE − YMPE) × rate2; cap of T4 box 26 | T4127 122nd ed. table 8.6 (2026), 8.27 (2025); CRA CPP2 rates page (2027); CPP s. 18.1 |
| `l10n_ca.cpp.basic_exemption` | 3,500 | 3,500 | — | Exemption per pay 3,500 / P truncated to the cent in C = rate × (PI − 3,500 / P) | T4127 122nd ed. ch. 6, table 6.1, table 8.3; CPP s. 19-20 |
| `l10n_ca.cpp.rate` | 0.0595 → 5.95% | 0.0595 → 5.95% | 0.0575 → 5.75% | Rate of C between the exemption and the YMPE; employer pays the same | T4127 122nd ed. table 8.3, 8.24; S.C. 2026, c. 22 (2027); CPP s. 8, Schedule 1 |
| `l10n_ca.cpp.base_rate` | 0.0495 → 4.95% | 0.0495 → 4.95% | 0.0475 → 4.75% | Base share C × base / rate enters K2; the rest of C is the first additional contribution of F5 | T4127 122nd ed. table 8.4, 8.25; S.C. 2026, c. 22 (2027); CPP s. 8 |
| `l10n_ca.cpp.rate2` | 0.04 → 4% | 0.04 → 4% | — | C2 = rate2 × (PIYTD + PI − W), up to the maximum C2; employer pays the same | T4127 122nd ed. table 8.6, 8.27; CPP s. 8, Schedule 2 |
| `l10n_ca.cpp.age_min` | 18 | — | — | Contributions start with the first pay dated in the month after the 18th birthday; PM counts the months from that month | T4127 122nd ed. ch. 6; CPP s. 12(1) |
| `l10n_ca.cpp.age_max` | 70 | — | — | Contributions stop after the last pay dated in the month of the 70th birthday; PM ends with that month | T4127 122nd ed. ch. 6; CPP s. 12(1) |

Derived figures:

- **Maximum C** = (YMPE − 3,500) × 5.95%, rounded to the cent. 2025:
  67,800 × 0.0595 = **4,034.10** (T4127 122nd ed. table 8.24). 2026:
  71,100 × 0.0595 = **4,230.45** (table 8.3). The code prorates it by
  PM / 12 for an employee who reaches 18 or 70 during the year.
- **Maximum base contribution** (cap of the CPP part of K2)
  = (YMPE − 3,500) × 4.95%. 2025: 67,800 × 0.0495 = **3,356.10** (table
  8.25). 2026: 71,100 × 0.0495 = **3,519.45** (table 8.4).
- **First additional contribution**, the part of C in F5, is C × 1% /
  5.95%; at the maximum, 2025: 678.00 (table 8.26), 2026: 711.00
  (table 8.5).
- **Maximum C2** = (YAMPE − YMPE) × 4%. 2025: 9,900 × 0.04 = **396.00**
  (table 8.27). 2026: 10,400 × 0.04 = **416.00** (table 8.6).
- **Exemption per pay** = 3,500 / P truncated to the cent: 291.66
  (P = 12), 145.83 (24), 134.61 (26), 129.62 (27), 67.30 (52), 66.03 (53),
  875.00 (4), 1,750.00 (2), 3,500.00 (1). Matches T4127 122nd ed.
  table 6.1.
- **2027.** Maximum C = (76,700 − 3,500) × 5.75% = 73,200 × 0.0575 =
  **4,209.00**; maximum base contribution 73,200 × 0.0475 = 3,477.00;
  first additional contribution at the maximum 732.00; maximum C2 =
  (87,400 − 76,700) × 4% = 10,700 × 0.04 = **428.00**. The two bold
  figures are the 2027 rows of the CRA CPP and CPP2 pages.
- **QPP.** An employment in Quebec reads the same keys under `l10n_ca.qpp.`;
  they come with the Quebec payroll module, and the payslip stops with an
  error when no QPP rate is in force.

### Employment insurance

| Parameter | 2025 | 2026 | 2027 | What the computation does with it | Source |
|---|---|---|---|---|---|
| `l10n_ca.ei.mie` | 65,700 | 68,900 | 70,800 | Maximum premium = MIE × rate; cap of T4 box 24 | T4127 122nd ed. table 8.7 (2026), 8.28 (2025); ESDC 2027 release; EIA s. 4 |
| `l10n_ca.ei.rate` | 0.0164 → 1.64% | 0.0163 → 1.63% | 0.0164 → 1.64% | EI = min(maximum − D1, rate × IE) outside Quebec; enters K2 | Same; EIA s. 66 |
| `l10n_ca.ei.rate_qc` | 0.0131 → 1.31% | 0.0130 → 1.30% | 0.0129 → 1.29% | Same formula for an employment in Quebec | Same; EIA s. 69 |
| `l10n_ca.ei.employer_multiplier` | 1.4 | — | — | Employer premium = 1.4 × employee premium of the pay, unless the company sets a reduced multiplier (Premium Reduction Program) | T4127 122nd ed. table 8.7 (employer rate); EIA s. 68 |

Derived figures:

- **Maximum employee premium** = MIE × rate, rounded to the cent. 2025:
  65,700 × 0.0164 = **1,077.48**; Quebec 65,700 × 0.0131 = **860.67**
  (T4127 122nd ed. table 8.28). 2026: 68,900 × 0.0163 = **1,123.07**;
  Quebec 68,900 × 0.0130 = **895.70** (table 8.7). 2027: 70,800 × 0.0164
  = **1,161.12**; Quebec 70,800 × 0.0129 = **913.32** (ESDC 2027 release).
- **Maximum employer premium** = 1.4 × maximum employee premium. 2025:
  **1,508.47**, Quebec **1,204.94** (table 8.28). 2026: **1,572.30**,
  Quebec **1,253.98** (table 8.7). 2027: 1,625.57, Quebec 1,278.65; the
  ESDC release gives the employer rate rounded to 2.30 and 1.81 per 100.
- **Employer rate** = 1.4 × 1.63% = 2.282% in 2026 (table 8.7: 0.02282).

### Remittances and T4

| Parameter | 2025 (and later) | What the computation does with it | Source |
|---|---|---|---|
| `l10n_ca.pd7a.due_day` | 15 | Regular remitter: one period per month, due the 15th of the next month. Quarterly remitter: one period per quarter, due the 15th of the month after the quarter | T4001 "Remittance due dates"; ITR s. 108(1) |
| `l10n_ca.pd7a.accel1_split_day` | 15 | Threshold 1: the month splits after the 15th | T4001; ITR s. 108(1.1) |
| `l10n_ca.pd7a.accel1_first_due_day` | 25 | Threshold 1: pays of the 1st to the 15th are due the 25th of the same month | T4001; ITR s. 108(1.1) |
| `l10n_ca.pd7a.accel1_second_due_day` | 10 | Threshold 1: pays of the 16th to the end of the month are due the 10th of the next month | T4001; ITR s. 108(1.1) |
| `l10n_ca.pd7a.accel2_period_end_days` | [7, 14, 21] | Threshold 2: periods 1-7, 8-14, 15-21 and 22 to the end of the month | T4001; ITR s. 108(1.1)(b) |
| `l10n_ca.pd7a.accel2_working_days` | 3 | Threshold 2: due 3 working days (Monday to Friday) after the end of the period | T4001; ITR s. 108(1.1)(b) |
| `l10n_ca.t4.due_month` | 2 | T4 slips and Summary due on the last day of February of the year after the slips | T4001 "Filing information returns"; ITR s. 205(1) |

Derived figures:

- A due date of a regular, quarterly or threshold 1 remitter that falls on
  a Saturday or a Sunday moves to the next Monday, as T4001 accepts a
  payment received on the next business day. Public holidays are not
  known to the module and do not move the date.
- The parameters are read at the end of each remittance period, and the T4
  month on January 1 of the following year: a version dated in the year
  changes the periods that end after it.
- The T4 due date is the last day of the month, moved to the next Monday
  when it falls on a Saturday or a Sunday, as for the remittances:
  February 28, 2027 is a Sunday, so the 2026 slips are due March 1, 2027.

### Worked examples

The tests compute payslips in 2026 with the shipped parameters and assert
these amounts (`tests/test_payroll.py`).

- **Monthly pay of 5,000 in New Brunswick** — exemption 291.66;
  C = 0.0595 × 4,708.34 = 280.15; C2 = 0; EI = 0.0163 × 5,000 = 81.50,
  employer 114.10; F5 = 47.08 (rounded to the cent); A = 12 × (5,000 − 47.08) = 59,435.04,
  R = 20.5%, K = 3,804; K1 = 2,303.28; K2 = 0.14 × (2,796.79 + 978)
  = 528.47; K4 = 210.14; T3 = 5,338.29; **federal tax 444.86**.
  `test_monthly_new_brunswick`
- **Bi-weekly pay** — monthly wage 5,200 → 2,400 per pay (P = 26);
  exemption 134.61; C = 134.79; EI = 39.12, employer 54.77;
  A = 61,811.00; K2 = 550.57; T3 = 5,803.26; **federal tax 223.20**.
  `test_biweekly`
- **Low income** — 1,000 a month: C = 42.15, EI = 16.30, A = 11,914.99,
  0.14 × A = 1,668.10 < K1 = 2,303.28: **no federal tax**.
  `test_low_income_no_tax`
- **Basic personal amount phase-out** — 25,000 a month: C = 1,470.15,
  EI = 407.50, A = 297,034.99 ≥ 258,482 → BPAF 14,829, K1 = 2,076.06,
  R = 33%, K = 26,024, K2 = 649.95 (both maximums); T3 = 69,061.39;
  **federal tax 5,755.12**. `test_basic_personal_amount_phase_out`
- **TD1 claim code 0 and additional tax** — 5,000 a month, TC = 0:
  T3 = 5,338.29 + 2,303.28 = 7,641.57 → 636.80, plus 50.00 requested:
  **686.80**. `test_td1_claim_and_additional_tax`
- **CPP and EI exemptions** — 5,000 a month: A = 60,000, K2 = 0,
  T3 = 5,982.58, **federal tax 498.55**. `test_exemptions`
- **Year-to-date maximums, T4 and remittance** — 15,000 a month,
  January to July. CPP 875.15 × 4, then 729.85, then 0: total
  **4,230.45** (table 8.3). CPP2 16.00 in May, 400.00 in June: total
  **416.00** (table 8.6). EI 244.50 × 4, then 145.07: total **1,123.07**
  (table 8.7); employer EI **1,572.30**. Federal tax 2,744.73 (months 1-4,
  A = 178,234.99, K = 10,241, K2 = 649.95), 2,746.92, 2,678.97, 2,782.97.
  T4 box 24 capped at **68,900**, box 26 at **85,000**; T4 due
  2027-03-01 (February 28 is a Sunday). January remittance 5,081.83, due
  2026-02-16 (February 15 is a Sunday). `test_maximums_t4_and_remittances`
- **Refund** — a refunded January payslip leaves February as a first pay:
  CPP 875.15, EI 244.50. `test_refund_reduces_year_to_date`
- **CPP at 70** — 70th birthday in March: PM = 3, maximum 4,230.45 × 3 /
  12 = 1,057.61; CPP 875.15, 182.46, 0, then not pensionable in April.
  `test_cpp_stops_at_70`
- **CPP at 18** — 18th birthday in March: no CPP in March, 280.15 in
  April. `test_cpp_starts_after_18`
- **RPP and RRSP contributions (F)** — 5,000 a month in New Brunswick, RPP of
  300 on the contract and RRSP of 100 in the payslip input: F = 400,
  A = 12 × (5,000 − 400 − 47.08) = 54,635.04, R = 14%, K = 0;
  T3 = 4,607.01, **federal tax 383.92** instead of 444.86. CPP, EI and
  box 14 keep the gross of 5,000; box 20 is 300.
  `test_rpp_and_rrsp_lower_the_taxable_income`
- **Union dues and support payments (U1, F2)** — 5,000 a month in
  New Brunswick, union dues of 50 on the contract and a support payment of 100
  in the payslip input: A = 12 × (5,000 − 150 − 47.08) = 57,635.04,
  R = 14%; T3 = 5,027.01, **federal tax 418.92**; box 44 is 50.
  `test_union_dues_and_support_lower_the_taxable_income`
- **Transfer from QPP to CPP** — 10,000 a month, January to June in
  Quebec (QPP 611.63 a month, DQ = 3,669.78), then New Brunswick: DQ counts
  as 3,669.78 × 0.0595 / 0.063 = 3,465.90 of CPP, so C = 577.65 in July,
  186.90 in August, then 0; K2R raises the maximum of the base credit to
  3,519.45 + 3,669.78 × 0.0035 / 0.063 = 3,723.33.
  `test_transfer_from_qpp_to_cpp`
- **Bonus without regular pay** — after three pays of 5,000, a pay of a
  bonus of 10,000 alone takes I of the most recent regular pay (T4127): A
  goes from 59,435.04 to 69,337.96, K2 adds 90.10, **TB = 1,940.00**. With
  no regular pay before it, the payslip warns that the bonus is taxed as the
  only income of the year. `test_bonus_without_regular_pay`
- A pay of a year whose indexed amounts are not entered (no version of
  `l10n_ca.federal.bpa_max` dated in that year) is computed with the last
  ones and the payslip warns about it.
- **2027 maximums** — 30,000 a month in 2027: CPP 1,708.23 × 2, then
  792.54 (maximum **4,209.00**); CPP2 **428.00** in March; EI 492.00 × 2,
  then 177.12 (maximum **1,161.12**). `test_maximums_2027`
- **T4127 regular bonus example** — 1,000 a week, an earlier bonus of
  1,500 (F5B 14.60) and a bonus of 2,500 payable now: C = 204.25,
  F5A = 9.81, F5B = 24.52, EI = 57.05; regular tax 81.55; K2 adds 23.03
  for the contributions on the bonus; **TB = 0.14 × 2,475.48 − 23.03
  = 323.54**, the TB of the T4127 122nd edition example.
  `test_bonus_example_t4127`
- **Bonus flat rate** — 200 a month and a bonus of 1,000: A with the bonus
  ≤ 5,000, **TB = 150.00** (15%); in Quebec **100.00** (10%).
  `test_bonus_flat_rate`
- **Quebec abatement** — 5,000 a month in Quebec with the 2026 QPP rates
  of T4127 table 8.3/8.4 (6.30%, base 5.30%): QPP 296.63, EI 1.30% = 65.00,
  employer 91.00; K2 = 528.44; T3 = 5,338.32; T1 = 0.835 × T3;
  **federal tax 371.46**. `test_quebec_federal_abatement`
- **QPIP credit through the K2 hook** — the same pay with a QPIP item of
  0.43% (maximum 442.90, table 8.8): K2 + 36.12, **federal tax 368.95**.
  `test_quebec_k2_extension_point`
- **Transfer from CPP to QPP** — 40,000 a month, January in New Brunswick
  (CPP 2,362.65), then Quebec: the CPP withheld counts as 2,362.65 ×
  0.063 / 0.0595 = 2,501.63 against the QPP maximum 4,479.30; QPP
  1,977.67 in February, 0 in March with QPP2 216.00. With two months in
  New Brunswick (CPP 4,230.45, CPP2 216.00), QPP is 0 and QPP2 200.00 in
  April. Reproduces the transfer formula of TP-1015.F 2026 part 3.1.
  `test_transfer_from_cpp_to_qpp`
- **Remittance periods of 2026** — quarterly: 4 periods, Q1 due
  2026-04-15, Q4 due 2027-01-15. Threshold 1: 24 periods, January 1-15 due
  2026-01-26 (January 25 is a Sunday), January 16-31 due 2026-02-10.
  Regular: July due 2026-08-17 (August 15 is a Saturday), October due
  2026-11-16, December due 2027-01-15. Threshold 2: 48 periods, January
  1-7 due 2026-01-12, January 22-31 due 2026-02-04.
  `test_remittance_periods`
- **Employees of the PD7A** — a monthly and a bi-weekly payroll in March
  count 2 employees in the last pay period, 3 payslips.
  `test_remittance_counts_each_payroll`

### Updating for a new year

- Read the January edition of T4127 (effective January 1): chapter 2
  (BPAF formula: maximum, minimum, phase-out start and end) and chapter 8
  tables 8.1 to 8.7, and add a version dated January 1 to each parameter
  that changes. A mid-year change of rates comes with a July edition of
  T4127 and a version dated July 1, as for 2025.
- The CRA announces the next year's YMPE and YAMPE in the fall, and the
  indexed federal amounts at the latest with the January edition of
  T4127; for 2027, the EI Commission confirmed the EI rate and maximum
  insurable earnings on September 14, 2026 (release above).
- Change every year: the bracket thresholds, BPAF maximum and minimum,
  phase-out start and end (the 4th and 5th thresholds) and the CEA, all
  indexed (ITA s. 117.1); the YMPE and YAMPE; the EI maximum insurable
  earnings and rates.
- Change only when the governing text changes: the bracket rates and
  `l10n_ca.federal.credit_rate`, which stays equal to the lowest rate, the
  Quebec abatement, the CPP basic exemption, rates and ages, and the EI
  employer multiplier (a law or a budget); the remittance days and the T4
  month (the Income Tax Regulations); the bonus threshold and flat rates
  (the T4127 note).
- Check the result against the derived figures above: maximum
  contributions and premiums of tables 8.3 to 8.7, and the K constants of
  table 8.1, which the code recomputes from the bracket table.
