Canadian federal payroll on top of the OCA payroll.

- Salary structure *Canada - Base*: basic salary, gross, CPP/QPP, CPP2/QPP2,
  EI, federal income tax, provincial income tax, net pay and the employer
  CPP, CPP2 and EI contributions.
- Deductions computed with the CRA *Payroll Deductions Formulas* (T4127,
  option 1): annualized income, federal tax `T3 = R*A - K - K1 - K2 - K3 -
  K4` with the basic personal amount phase-out and the Canada employment
  amount, CPP base and first additional contributions with the basic
  exemption per pay period, CPP2 between the YMPE and the YAMPE, EI up to
  the maximum insurable earnings, employer EI at 1.4 times the employee
  premium. Year-to-date maximums come from the done payslips of the
  calendar year.
- Bonuses, retroactive pay increases and other non-periodic payments: the
  *Bonus* input of the payslip, or any rule of category *Bonuses and
  Lump-Sum Payments*, is part of the gross and of the CPP and EI
  earnings, but only the regular pay is annualized. The federal tax on the
  payment is the regular bonus calculation of T4127 (tax on the annual
  income with the payment less the tax without it, previous payments of
  the year included), or a flat rate when that income is at most 5,000.
  RPP or RRSP contributions withheld from the payment go in category
  *Deduction From a Bonus or Lump-Sum Payment*.
- RPP, RRSP, PRPP and VRSP contributions withheld from the regular pay: an
  amount per pay on the contract, plus the *RPP Contribution* or *RRSP
  Contribution* input of the payslip, in category *Deduction Reducing the
  Taxable Income* (`CA_TAX_DED`). They lower the annual taxable income
  (F of T4127), not the CPP and EI earnings; the RPP contributions are
  reported in box 20 of the T4.
- Union dues and support payments under a legal document dated before
  May 1, 1997, also an amount per pay on the contract plus a payslip
  input, in category *Deduction Reducing the CRA Taxable Income*
  (`CA_FED_TAX_DED`): they lower A (U1 and F2 of T4127) for the federal
  and provincial tax of the CRA formulas, not the Quebec tax. Union dues
  go in box 44 of the T4.
- Every rate, ceiling, bracket table, credit amount and due date is a dated
  time parameter (`l10n_ca.federal.*`, `l10n_ca.cpp.*`, `l10n_ca.ei.*`,
  `l10n_ca.pd7a.*`, `l10n_ca.t4.*`) shipped for 2025 and 2026, and 2027
  where already published.
- Contract fields: province of employment, pay periods per year, federal
  TD1 claim, additional tax, other federal credits, RPP and RRSP
  contributions, union dues and support payments per pay, CPP/QPP and EI
  exemptions. The birth date of the
  employee applies the CPP age limits.
- Provincial income tax is left to one module per province. Without one,
  the payslip shows a *NOT COMPUTED* line and a warning instead of a
  silent zero.
- Year-end: T4 slips per employee and province (boxes 10, 12, 14, 16, 16A,
  17, 17A, 18, 20, 22, 24, 26, 28, 44, 45), T4 Summary lines 14 to 88, PD7A
  remittances per period of the remitter type, CSV exports to fill in the
  CRA web forms.
- Accounting through `payroll_account`, with accounts proposed from the
  `ca_2023` chart.

Extension points for a provincial module, on `hr.payslip`:
`_l10n_ca_pension_plan`, `_l10n_ca_ei_rate`,
`_l10n_ca_compute_other_contributions`, `_l10n_ca_federal_k2_items`,
`_l10n_ca_federal_abatement`, `_l10n_ca_provincial_tax`,
`_l10n_ca_t4_values`, `_l10n_ca_remittance_values`. Employees working in
Quebec contribute to the QPP, whose rates (`l10n_ca.qpp.*`) come with the
Quebec payroll module.

Common engine of the provinces whose income tax the CRA collects
(`models/hr_payslip_province.py`): a province module registers its code
and the prefix of its time parameters in `_l10n_ca_province_prefixes`,
and the engine applies T4127 option 1, steps 4 to 6 (T4 = V x A - KP -
K1P - K2P - K3P - K4P - K5P, T2 = T4 + V1 + V2 - S - P x LCP, (T1 + T2) /
P rounded once), the provincial tax on bonuses, the employer payroll tax
of the province (rate by total remuneration, exemption consumed by the
first pays of the year) and the workers' compensation premium (rate per
$100 up to the maximum insurable earnings). The factors only some
provinces have are hooks: `_l10n_ca_prov_bpa`,
`_l10n_ca_prov_extra_credits`, `_l10n_ca_prov_surtax`,
`_l10n_ca_prov_premium`, `_l10n_ca_prov_reduction`. The contract holds
the provincial TD1 (claim, other credits, additional tax), the
labour-sponsored fund shares withheld (rule CA_LSVCC, credit LCP) and the
workers' compensation exemption; Payroll > Configuration > Provincial
Payroll Accounts holds, per company and province, the employer tax rate
basis and exemption and the workers' compensation rate.
