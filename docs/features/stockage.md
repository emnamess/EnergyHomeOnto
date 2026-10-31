# Feature 3 — Stockage énergétique

Cette feature verticale décrit les systèmes de stockage du réseau (batteries,
supercondensateurs, stockage hydrogène), les sources qui les remplissent et les
bâtiments qu’ils alimentent. Elle a son interface React, son backend FastAPI et
ses requêtes SPARQL dédiées.

- Ontologie (déjà présente dans `energyhomeonto.owx`, non modifiée) :
  - `Stockage` → `Batterie` (`BatterieLithium`, `BatteriePlomb`), `SuperCondensateur`,
    `StockageHydrogene` (classes disjointes) ;
  - `capacite` (kWh, fonctionnelle), `niveauCharge` (% restreint à [0 ; 100]),
    `tempsRecharge`, `nombreCyclesCharge` (domaine `Batterie`), `dureeVie`,
    `coutInstallation`, `anneeInstallation` ;
  - `stockeDans` (source → stockage) et `alimente` (stockage → bâtiment), inverse `estAlimentePar` ;
  - classe définie `BatimentAvecStockage ≡ Batiment ⊓ ∃estAlimentePar.Stockage` ;
  - 5 individus : `batterie1`, `batterie2`, `batterie3`, `stockageH2_1`, `superCondo1`.
- Inférences exploitées :
  - filtre par type : `?s a :Batterie` renvoie aussi les batteries lithium et plomb (sous-classes) ;
  - bâtiments alimentés : `estAlimentePar` déduit de `alimente`, puis classement
    automatique en `BatimentAvecStockage` (affiché « Déduit » dans la fiche) ;
  - classes déduites de chaque stockage (`Batterie`, `Stockage`, `EquipementMaintenable`…).
- Calculs SPARQL : énergie disponible `BIND(?capacity * ?charge / 100)`, indicateurs
  par type avec `COUNT`, `SUM`, `AVG` et `GROUP BY`.
- Frontend : indicateurs globaux, liste filtrable (texte, type, niveau de charge,
  capacité minimale), fiche avec jauge de charge, sources, bâtiments et classes déduites ;
  création, modification et suppression avec affichage de la requête SPARQL Update.
- Backend :
  - `GET /api/stockages?kind=&q=&min_capacity=&charge=faible|moyen|eleve`
  - `GET /api/stockages/indicateurs`
  - `GET /api/stockages/options` (sources et bâtiments proposés dans le formulaire)
  - `GET /api/stockages/{id}`
  - `POST /api/stockages` (`INSERT DATA`)
  - `PUT /api/stockages/{id}` (`DELETE … INSERT … WHERE`)
  - `DELETE /api/stockages/{id}` (`DELETE WHERE`) ; refusé (409) si le stockage a un
    historique de maintenance (feature 6).
- Règles de cohérence : `nombreCyclesCharge` n’est accepté que pour une batterie
  (son domaine est `Batterie`, disjointe des autres types) ; les sources et bâtiments
  reçus sont vérifiés par `ASK` ; toutes les valeurs passent par `string()` / `number()`.
- Recherche intelligente : synonymes ajoutés (accumulateur, supercondensateur, plomb,
  lithium, réserve, cycle, durée de recharge, bâtiment secouru) et verbes
  (remplir, recharger, charger, accumuler → `stockeDans`). Exemples :
  « bâtiments avec batterie », « batteries avec plus de 2000 cycles »,
  « stockages rechargés par un panneau solaire », « supercondensateurs ».
- Code : `frontend/src/features/stockage/` et `backend/app/features/stockage/` ;
  tests : `backend/tests/test_stockage.py`.
