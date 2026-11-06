1. On each asset, tab *Tax Depreciation (CCA)*: check the class, the
   available-for-use date and the capital cost. Tick *Previously Owned or
   Non-Arm's Length* when the property does not qualify for the incentives.
   Reduce the capital cost by government assistance or investment tax
   credits (for example a Quebec C3i credit).
2. Remove a sold asset with the *Remove* button: the sale value becomes the
   proceeds of disposition.
3. Invoicing (Accounting) > Assets > CCA Schedules: create the schedule of the
   taxation year. For the first year kept in Odoo, add one line per class
   with the opening UCC of the last return before generating.
4. *Generate from Assets*. Lower the *CCA Claimed* of a class to keep
   deductions for later years (for example when the small business
   deduction already brings the tax to a low rate, or to use losses).
   Clear *Property Remaining* when the last property of a pool is gone and
   the generation could not see it.
5. Report the totals: CCA on Schedule 1 line 403 (and Schedule 8),
   recapture line 107, terminal loss line 404, and the book amortization
   and gains or losses shown in the *Book to Tax Reconciliation* tab.
6. *Lock* the schedule once the return is filed; next year starts from its
   closing balances. *Print* gives the PDF.

Limits: no half-year rule exceptions other than the class 12 threshold, no
additional allowance of class 1 buildings, no special rules for taxation
years straddling two calendar years under the incentives, no allocation
of the CCPC limit among associated corporations (enter the allocated limit
as a company parameter `l10n_ca.cca.diep.limit`).
