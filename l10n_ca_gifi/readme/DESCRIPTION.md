General Index of Financial Information (GIFI) of the Canada Revenue
Agency, used to file the financial statements with the T2 return
(schedules 100, 101, 125 and 141) and with the Quebec CO-17 return.

- The complete GIFI of guide RC4088 (Rev. 23): 766 items from 1000 to
  9999, with their category, schedule, lead item and the total each one
  rolls into. Totals and calculated items (1599, 2599, 3499, 3620, 3849,
  8299, 8518, 8519, 9368, 9369, 9970, 9999, ...) are computed, never
  mapped.
- A GIFI code on every account. The 341 accounts of the Canadian chart
  (ca_2023) are mapped at installation and on every new company; an
  account without code falls back on the code set for its account type.
- A GIFI statement per fiscal year: Schedule 100 at year end with the
  retained earnings roll-forward (3660, 3680, 3700, 3849), Schedule 125
  for the year, Schedule 101 for the first year after incorporation,
  amounts in whole dollars with the sign convention of the schedules.
- The validity checks of the CRA (total assets equal liabilities plus
  equity, 3849 equals 3600, 3680 equals 9999, 9369 equals revenue less
  expenses), unmapped accounts, accounts mapped across schedules and
  amounts of an unexpected sign.
- Exports: CSV `code,amount` per schedule for the import of the T2 and
  CO-17 software, XLSX workbook and PDF.
