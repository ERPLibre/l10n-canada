1. Invoicing (Accounting) > Configuration > Settings > *Canadian Tax Profile* (module
   `l10n_ca_time_parameter`): filing frequencies of GST/HST and QST,
   income tax instalments, CRA remitter type, CCPC status.
2. Same page, *Canadian Tax Calendar*:
   - responsible user, reminder delay (days before the due date) and
     horizon (months of deadlines created ahead);
   - net GST/HST and QST of the previous year: an annual filer reaching the
     instalment threshold (time parameters
     `l10n_ca.tax_calendar.gst_instalment_threshold` and
     `qst_instalment_threshold`) gets quarterly instalments;
   - T5 / RL-3 slips, Revenu Quebec remittance frequency when it differs
     from the CRA one (Revenu Quebec also has an annual frequency the CRA
     does not), Quebec income tax instalment frequency when it differs
     from the federal one, annual updating declaration combined with the
     CO-17.
3. The fiscal year end of the company (accounting settings) anchors the
   fiscal periods.
4. Invoicing (Accounting) > Canada > Public Holidays: add the holidays of the years
   after 2027 (the *Create Next Year Public Holidays* wizard of
   `calendar_public_holiday` copies the fixed dates; move the others).
   Mark the days Revenu Quebec is closed without a legal holiday with
   *Revenu Quebec closed (source deductions)*.
5. Invoicing (Accounting) > Canada > Deadline Rules: archive a rule that does not apply,
   change its condition or responsible, or add a rule of your own.
   Invoicing (Accounting) > Configuration > Canadian Time Parameters holds the timings.
