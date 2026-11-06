Tax depreciation (capital cost allowance, CCA) of a Canadian corporation,
computed next to the book depreciation of `account_asset_management`.

- **CCA classes** (1, 8, 10, 10.1, 12, 13, 14, 14.1, 17, 43, 44, 46, 50,
  53, 54, 55): method (declining balance, straight-line for classes 13 and
  14, 100% for class 12), half-year rule, eligibility to the accelerated
  investment incentive and to the CCPC immediate expensing, separate class
  per property (10.1). Rates, prescribed cost limits, half-year factor and
  every incentive window are dated parameters
  (`l10n_ca.cca.class_<n>.rate`, `l10n_ca.cca.aiip.windows`,
  `l10n_ca.cca.class_<n>.expensing`, ...), so a budget is a data change.
- **Shipped rules**: accelerated investment incentive (AIIP, property
  acquired after 2018-11-20) and reaccelerated investment incentive (RIIP,
  property acquired after 2024, enhanced allowance until 2029, phase-out
  2030-2033) enacted by Bill C-15 (Royal Assent 2026-03-26); 100%
  first-year write-off of classes 44, 46 and 50 acquired and available for
  use after 2024-04-15 and before 2027, then full cost without the
  half-year rule for those acquired after 2024 and available for use before
  2034; immediate expensing of zero-emission vehicles (54, 55) and
  manufacturing machinery (53, 43); CCPC designated
  immediate expensing ($1.5M, property available for use before 2024);
  class 10.1 and 54 cost limits for 2025 ($38,000 / $61,000) and 2026
  ($39,000 / $61,000).
- **Assets and profiles** carry a CCA class, an acquisition date, an
  available-for-use date, the capital cost (limited for classes 10.1 and
  54), an exclusion flag for previously owned or non-arm's length property,
  the immediate expensing flag and the proceeds of disposition (filled by
  the removal wizard).
- **CCA schedule** per company, taxation year and jurisdiction (federal
  T2 Schedule 8, or Quebec CO-17 which reads `l10n_ca.cca.qc.*` parameters
  before the federal ones): opening UCC, additions split between regular,
  accelerated and expensed property, dispositions (lesser of proceeds and
  capital cost), CCA base, maximum CCA, CCA claimed (any amount up to the
  maximum), recapture, terminal loss and closing UCC. Short taxation years
  are prorated. A locked schedule gives its closing balances to the next
  year.
- **Book to tax reconciliation**: book depreciation posted in the year
  per class against the CCA claimed, and the Schedule 1 adjustments
  (amortization, recapture, book gain or loss, CCA, terminal loss), in the
  form and in a PDF report.
