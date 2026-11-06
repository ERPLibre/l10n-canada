Compliance calendar of a Quebec corporation: the filing and payment
deadlines of the Canada Revenue Agency, Revenu Quebec, the Registraire des
entreprises and the CNESST, generated from the tax profile of the company,
with a reminder activity before each due date.

- **Deadline rules** (`l10n.ca.tax.deadline.rule`), shipped as editable
  data: GST/HST and QST returns, payments and instalments; federal and
  Quebec corporate income tax instalments, balances, T2 and CO-17 returns;
  source deduction remittances for each remitter type; T4, T5, RL-1, RL-3
  summaries and the Health Services Fund reconciliation; CNESST statement
  of wages; annual updating declaration and registration fee of the
  enterprise register.
- Each rule has a condition on the company (a domain on its tax profile),
  a period (fiscal month, quarter or year, calendar month, half month,
  quarter of month, calendar quarter or year), and a timing read from a
  dated time parameter `l10n_ca.tax_calendar.timing_<rule>`: months and
  days after the period end, business days, or a fixed day of a month.
  A change of law is a new parameter version; past periods keep their
  deadline.
- Weekend and holiday rule: a due date on a Saturday, a Sunday or a public
  holiday of the authority moves to the next business day. The holidays
  come from OCA `calendar_public_holiday`, each line telling whether it
  moves federal deadlines, Quebec deadlines or both. The source deduction
  remittances to Revenu Quebec also skip the days its offices are closed
  (December 24 and 31, January 2, and the closures moved off a weekend),
  as its employer guide states; its other deadlines do not.
- Installation loads the holidays of Canada for 2025 to 2027. A year
  already present in the database is completed with the missing dates
  instead of being created again.
- **Deadlines** (`l10n.ca.tax.deadline`): one per rule, company and
  period, with its due date, state, responsible and reminder activity; list,
  calendar and kanban views under *Invoicing (Accounting) > Canada > Tax Deadlines*.
- A daily scheduled action creates the deadlines due in the coming months
  and the reminder activities; marking the reminder done closes the
  deadline.
