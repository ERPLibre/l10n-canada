Bridge between *Canada - Owner-Manager Corporate Tax* and *Canada - Capital
Cost Allowance*, installed automatically when both are.

*Load from Accounting* on a corporate tax estimate adds the T2 Schedule 1
items of the federal CCA schedule whose taxation year ends on the last day
of the estimate's fiscal year:

| Schedule 1 item                       | Adjustment to accounting income |
|---------------------------------------|---------------------------------|
| Capital cost allowance (line 403)     | deducted                        |
| Recapture of CCA (line 107)           | added                           |
| Terminal loss (line 404)              | deducted                        |
| Book gain on disposal (line 401)      | deducted (reversed)             |
| Book loss on disposal (line 111)      | added (reversed)                |

Book amortization (line 104) is read from the ledger, not from the
schedule, so that it matches the accounting income of the estimate. The
corporate tax module already adds back the balance of the accounts of type
*Depreciation*. This module adds back the depreciation entries of the
assets posted to other profit and loss accounts, so book depreciation is
counted once whatever account the asset profiles use. Accounts whose
corporate tax treatment is *Non-deductible* or *Meals* are left to the
corporate tax module.

The estimate keeps one taxable income for the federal and the Quebec
computations, and it is computed with the **federal** schedule. When a
Quebec CCA schedule exists for the same year and its Schedule 1 items
differ from the federal ones, the estimate shows a warning with the
difference of Quebec taxable income; the Quebec tax of the estimate is then
off by that difference times the Quebec rate. The CO-17 itself must be
prepared with the Quebec schedule.

The estimate also warns when the company has assets with a CCA class but no
federal schedule for the year, and when the federal schedule no longer
matches the CCA lines loaded on the estimate.
