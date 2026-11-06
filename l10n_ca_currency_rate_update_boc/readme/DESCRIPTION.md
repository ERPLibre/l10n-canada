Adds the Bank of Canada as a provider of the OCA *Currency Rate Update*
module.

- Rates come from the Valet API of the Bank of Canada, group
  `FX_RATES_DAILY`: one series `FX<CUR>CAD` per currency, giving the
  number of Canadian dollars for one unit of the currency, published each
  business day around 16:30 Eastern time.
- One request covers every selected currency and the whole date range.
- A company in CAD gets `1 / value`, the Odoo convention being the number of
  units of the currency for one unit of the company currency. A company in
  another supported currency gets cross rates through the CAD.
- Weekends and Bank of Canada holidays have no observation and create no
  rate: Odoo uses the last rate known before the date of a transaction.
