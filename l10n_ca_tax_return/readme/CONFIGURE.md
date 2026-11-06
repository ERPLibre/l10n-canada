Invoicing (Accounting) > Configuration > Settings > Canadian Tax Profile: filing
frequencies and quick method election (activity and effective date).

Invoicing (Accounting) > Configuration > Settings > Canadian Sales Tax Returns:

- *GST/HST Return Account*: account of the Canada Revenue Agency, which
  receives the net tax of the GST34 returns.
- *Revenu Quebec Account*: receives the net GST/HST and QST of the FPZ-500
  returns. A Quebec registrant files both taxes with Revenu Québec.
- *Quick Method Gain Account*: income account of the quick method difference.
- *Sales Tax Closing Journal*: miscellaneous journal of the closing and bad
  debt entries.
- *Bad Debt Expense Account* and *Bad Debt Recovery Account*.

On the `ca_2023` chart, the return accounts default to 221210 "Owing to
Governments" and the gain account to 413300 "All Other Operating Revenue".

The quick method remittance rates of the GST/HST are shipped for a permanent
establishment where the GST at 5% applies (Quebec included). A company whose
permanent establishment is in a participating province adds a company version
of `l10n_ca.gst_quick.rates.service` or `.resale` with its column of the CRA
table, under Invoicing (Accounting) > Configuration > Canadian Time Parameters.

Optionally, define the reporting periods as date ranges (OCA `date_range`) to
pick them on the return.
