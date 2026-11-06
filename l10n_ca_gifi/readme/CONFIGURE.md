Invoicing (Accounting) > Configuration > Accounting > Accounts without
GIFI Code: give a GIFI code to the accounts you created. Accounts of the
Canadian chart already have one; review them, the chart is generic and
an IT services company reports, for instance, its vendor bills under
8320 (cost of sales) until the expense accounts are remapped to
operating expenses. The GIFI statement warns when 8320 has an amount
while no inventory is reported.

Invoicing (Accounting) > Configuration > Accounting > GIFI Codes by
Account Type: code used for an account without its own code. A row of a
company wins over a row without company.

Retained earnings: create an equity account for the dividends declared
and give it GIFI code 3700. Entries posted directly on an account mapped
to 3600 during the year are reported under 3740 with a warning.

Invoicing (Accounting) > Configuration > Settings > Canadian Tax Profile
> GIFI Closing Journals: journals of the year-end closing and reopening
entries, ignored by the GIFI statement. The closing entries of the OCA
module `account_fiscal_year_closing` are ignored without configuration.

Invoicing (Accounting) > Configuration > Canadian Time Parameters: the
GIFI-Short limits (`l10n_ca.gifi.short_max_gross_revenue`,
`l10n_ca.gifi.short_max_assets`).
