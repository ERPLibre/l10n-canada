Shared foundation of the Canadian localization modules.

- Dated fiscal parameters stored with `base_time_parameter`: every rate,
  threshold or bracket table has one version per effective date, so a new
  year or a budget is a data change made in the interface, and past periods
  keep the value that applied to them.
- `res.company._l10n_ca_param(code, date)` reads a parameter: a company
  parameter wins over a parameter without company, a value of 0 is a value,
  and a missing parameter raises an error that names it.
- `tools.progressive_tax` and its siblings compute bracket tables stored as
  JSON `[[threshold, rate], ...]`.
- A *Canadian Tax Profile* section in the accounting settings: filing
  frequencies, quick method, instalments, payroll remitter type, CCPC
  status and Quebec enterprise number.
