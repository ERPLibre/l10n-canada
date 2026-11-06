1. Invoicing (Accounting) > Configuration > Settings > Currencies: enable
   *Automatic Currency Rates (OCA)*.
2. Invoicing (Accounting) > Configuration > Currency Rates Providers: create a provider
   with *Provider* = *Bank of Canada* and choose the currencies to update.
   The list offers the active currencies the Bank of Canada publishes
   daily: activate a currency first (Invoicing (Accounting) > Configuration >
   Currencies) when it is missing: a new database leaves most of them,
   the EUR included, inactive.
3. Keep the update interval at one day: the provider fetches every day from
   the last successful update to today.
