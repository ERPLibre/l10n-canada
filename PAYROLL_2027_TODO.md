# Paramètres de paie 2027 — à faire

Valeurs à partir du 1er janvier 2027 des paramètres temporels de
`l10n_ca_payroll` et `l10n_ca_qc_payroll`. Une valeur n'entre dans le XML
que lorsqu'une source officielle la publie : aucune n'est calculée ni
estimée. Les paramètres qui ne changent pas n'ont pas besoin d'une version
2027, la version 2026 reste en vigueur.

État au 12 novembre 2026.

## Ajoutées

| Paramètre | 2026 | 2027 | Source |
|---|---|---|---|
| `l10n_ca.cpp.ympe` | 74 600 | 76 700 | ARC, [Taux, maximums et exemptions du RPC](https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/canada-pension-plan-cpp/cpp-contribution-rates-maximums-exemptions.html), ligne 2027 |
| `l10n_ca.cpp.yampe` | 85 000 | 87 400 | ARC, [Taux et maximums du RPC2](https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/calculating-deductions/making-deductions/second-additional-cpp-contribution-rates-maximums.html), ligne 2027 |
| `l10n_ca.qc.cnesst.max_insurable` | 103 000 | 106 000 | CNESST, [Salaire maximum annuel assurable](https://www.cnesst.gouv.qc.ca/fr/demarches-formulaires/employeurs/assurance-sante-securite-travail/tarification/annexes-tableaux/salaire-maximum-annuel-assurable), année de tarification 2027 |

Contrôles : (76 700 − 3 500) × 5,75 % = 4 209,00 et (87 400 − 76 700) × 4 %
= 428,00, les maximums publiés par l'ARC pour 2027. Le test
`test_maximums_2027` calcule des paies de 2027 jusqu'à ces maximums.

## Déjà livrées, confirmées

| Paramètre | 2027 | Source |
|---|---|---|
| `l10n_ca.cpp.rate` | 0,0575 | ARC, page des taux du RPC, ligne 2027 |
| `l10n_ca.cpp.base_rate` | 0,0475 | T4127, 123e édition (juillet 2026) : taux de base de 9,90 % à 9,50 % au 1er janvier 2027 |
| `l10n_ca.ei.mie` | 70 800 | [Communiqué EDSC, septembre 2026](https://www.canada.ca/en/employment-social-development/news/2026/09/canada-employment-insurance-commission-confirms-2027-employment-insurance-premium-rate.html) ; ARC, taux de l'AE |
| `l10n_ca.ei.rate` | 0,0164 | Même communiqué |
| `l10n_ca.ei.rate_qc` | 0,0129 | Même communiqué |

Inchangés en 2027 selon les mêmes sources, sans nouvelle version :
`l10n_ca.cpp.basic_exemption` (3 500), `l10n_ca.cpp.rate2` (4 %),
`l10n_ca.federal.credit_rate` (14 %, LIR art. 117(2)) et
`l10n_ca.qc.hsf.payroll_max` (7,8 M$, « pour 2026 et les années
suivantes »).

## Manquantes

### Fédéral — T4127 de janvier 2027 (124e édition) ou page d'indexation de l'ARC

- [ ] `l10n_ca.federal.brackets` : seuils indexés ; les taux 14 / 20,5 / 26 /
      29 / 33 % ne changent pas
- [ ] `l10n_ca.federal.bpa_max`, `l10n_ca.federal.bpa_min`
- [ ] `l10n_ca.federal.bpa_phaseout_start`, `l10n_ca.federal.bpa_phaseout_end`
      (4e et 5e seuils des tranches)
- [ ] `l10n_ca.federal.canada_employment_amount`
- [ ] `l10n_ca.federal.qc_abatement` : 16,5 % prévu par la loi, à confirmer
      dans le T4127 2027 (aucune version à ajouter s'il ne change pas)

Le facteur d'indexation fédéral de 2027 n'est pas publié par l'ARC.

### Québec — impôt : Finances Québec (indexation 2027), TP-1015.F et TP-1015.G-V de janvier 2027

- [ ] `l10n_ca.qc.indexation_rate` : version 2027 obligatoire, sinon un
      TP-1015.3 d'une année antérieure ne peut pas être indexé
- [ ] `l10n_ca.qc.brackets`
- [ ] `l10n_ca.qc.bpa`
- [ ] `l10n_ca.qc.worker_deduction_max`
- [ ] `l10n_ca.qc.credit_rate`, `l10n_ca.qc.worker_deduction_rate`,
      `l10n_ca.qc.lump_sum_flat_rate` : aucun changement annoncé, à
      confirmer dans le TP-1015.F 2027

### Québec — RRQ : Retraite Québec

- [ ] `l10n_ca.qpp.ympe`, `l10n_ca.qpp.yampe` : la loi les aligne sur le
      MGAP et le MSGAP du RPC (76 700 et 87 400), mais Retraite Québec ne
      les a pas encore publiés
- [ ] `l10n_ca.qpp.base_rate`, `l10n_ca.qpp.rate` : la baisse à 5,30 % ne
      vise que 2026 ; le bulletin 2025-8 indique que l'art. 44.1 de la
      LRRQ s'applique de nouveau en 2027, sans taux publié
- [ ] `l10n_ca.qpp.rate2`, `l10n_ca.qpp.basic_exemption` : à confirmer

### Québec — RQAP et normes du travail

- [ ] `l10n_ca.qpip.mie` : égal par la loi au maximum de la CNESST
      (106 000 en 2027), à confirmer sur Québec.ca (RQAP)
- [ ] `l10n_ca.qpip.rate`, `l10n_ca.qpip.employer_rate` : taux 2027 du
      Conseil de gestion de l'assurance parentale
- [ ] `l10n_ca.qc.cnt.max_remuneration` : même montant que le maximum du
      RQAP, à confirmer chez Revenu Québec
- [ ] `l10n_ca.qc.cnt.rate`, `l10n_ca.qc.hsf.payroll_min`,
      `l10n_ca.qc.wsdrf.payroll_threshold` : fixés par la loi, aucun
      changement annoncé

Les pages de Revenu Québec et de LégisQuébec ont refusé la lecture
automatique (HTTP 403) : à consulter dans un navigateur.

## Pour chaque valeur publiée

1. Ajouter une version datée du 1er janvier 2027 dans
   `data/time_parameters.xml` du module.
2. Mettre à jour la colonne 2027 et les chiffres dérivés de la section
   « Parameters and their sources » de `readme/CONFIGURE.md`.
3. Recalculer l'exemple publié (tables du T4127, annexes du TP-1015.F) dans
   un test, puis cocher la ligne ici.
