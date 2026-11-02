# Feature 2 — Production énergétique

Sources d’énergie du réseau : panneaux solaires, éoliennes, centrales hydrauliques,
centrales thermiques et groupes électrogènes.

- **Ontologie** : `SourceEnergie` et ses sous-classes ; `SourceRenouvelable` /
  `SourceNonRenouvelable` (disjointes) ; classes définies `SourceForte`
  (puissance ≥ 50 kW), `SourceHautRendement` (rendement ≥ 80 %), `SourcePolluante`
  (émissions > 100 gCO₂/kWh) ; propriétés `puissance`, `rendement`,
  `productionAnnuelle`, `emissionCO2`, `alimente`, `stockeDans`, `possede`.
- **Inférences exploitées** : renouvelable ou non (sous-classes), classes définies
  par seuil, `estAlimentePar` (inverse de `alimente`) côté bâtiments, et
  `MaisonAutonome ≡ Maison ⊓ ∃possede.PanneauSolaire` : installer un panneau sur
  une maison la reclasse automatiquement.
- **Backend** (`backend/app/features/production/`) :
  - `GET /api/production/sources?kind=&renewable=&min_power=&q=` (filtres SPARQL)
  - `GET /api/production/sources/{id}` (détail, classes déduites, bâtiments, stockages, zone)
  - `GET /api/production/indicateurs` (agrégats `COUNT`/`SUM` : puissance, production, part renouvelable, CO₂ moyen)
  - `GET /api/production/options` (bâtiments, stockages et zones pour le formulaire)
  - `POST /api/production/sources` (`INSERT DATA`)
  - `PUT /api/production/sources/{id}` (`DELETE … INSERT … WHERE`)
  - `DELETE /api/production/sources/{id}` (`DELETE WHERE`, refusé si la source a des interventions)
- **Cohérence** : les caractéristiques propres à un type (surface et inclinaison
  d’un panneau, rotor d’une éolienne, combustible d’une centrale thermique…) sont
  refusées sur les autres types, car leur domaine dans l’ontologie le rendrait incohérent.
- **Frontend** (`frontend/src/features/production/ProductionPage.tsx`) : indicateurs,
  production par type, filtres, tableau, détail et formulaire adapté au type.
  `#/production?batiment=Maison10` ouvre le formulaire prérempli (alerte
  « maisons énergivores » du tableau de bord).
- **Recherche en français** : « sources fossiles », « quelle source produit le plus »,
  « panneaux installés après 2022 », « sources polluantes »…
- **Tests** : `backend/tests/test_production.py`.
