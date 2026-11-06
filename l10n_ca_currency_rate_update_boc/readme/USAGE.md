The scheduled action *Currency Rates Update* fetches the new rates. To load
a past period, use *Update Rates Wizard* on the provider with a start and
an end date: the business days of the period get one rate per currency.

A failure of the Valet API (network, unknown series) is posted in the
chatter of the provider and leaves the existing rates untouched.

The CRA accepts the Bank of Canada rate of the transaction day (or the
average rate of the year in some cases) to convert foreign currency
amounts, which is why a Canadian company usually prefers this provider.
