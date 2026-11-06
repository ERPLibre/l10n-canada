1. Invoicing (Accounting) > Configuration > Assets > CCA Classes: review the classes;
   the rate in force is read from the parameters.
2. Invoicing (Accounting) > Configuration > Canadian Time Parameters: the CCA
   parameters start with `l10n_ca.cca.`. Add a version when a budget
   changes a rate, a limit or an incentive window. For a Quebec rule that
   differs from the federal one, create the same code with the prefix
   `l10n_ca.cca.qc.`: the Quebec schedules read it first.
3. Invoicing (Accounting) > Configuration > Assets > Asset Profiles: set the default
   CCA class of each profile.
4. Invoicing (Accounting) > Configuration > Settings > Canadian Tax Profile: the CCPC
   status decides the CCPC immediate expensing.
