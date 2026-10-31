# Feature 6 — Maintenance et cycle de vie des équipements

Cette feature verticale suit l’âge, la fin de vie prévue et l’historique de
maintenance des équipements énergétiques. Elle a son interface React, son
backend FastAPI et ses requêtes SPARQL dédiées, sans dépendance vers les autres
features.

- Ontologie (ajoutée à `energyhomeonto.owx`) :
  - `EquipementMaintenable ≡ SourceEnergie ⊔ Stockage ⊔ EquipementReseau`
    (appartenance déduite par le raisonneur) ;
  - `Intervention` et ses sous-classes disjointes `InterventionPreventive` et
    `InterventionCorrective` ; chaque intervention concerne exactement un équipement ;
  - `concerne` (fonctionnelle) et son inverse `aSubi` ;
  - `dateIntervention` (`xsd:date`), `coutIntervention` (TND),
    `descriptionIntervention`, `prestataire` ;
  - classes définies `EquipementEntretenu ≡ EquipementMaintenable ⊓ ∃aSubi.InterventionPreventive`
    et `EquipementDejaRepare ≡ EquipementMaintenable ⊓ ∃aSubi.InterventionCorrective` ;
  - 5 interventions d’exemple (`intervention1` à `intervention5`).
- Données existantes exploitées : `anneeInstallation`, `dureeVie` et
  `coutInstallation`. L’âge et la durée de vie restante sont calculés en SPARQL
  (`BIND`) à partir de l’année en cours ; un équipement sans année d’installation
  est signalé « données manquantes ».
- Frontend : équipements filtrables par nom, catégorie et fin de vie prévue
  (≤ 3, 10 ou 15 ans) ; interventions filtrables par type et texte ; fiche
  équipement (âge, durée de vie restante, coûts, classes déduites, historique) ;
  création, modification et suppression d’interventions avec affichage de la
  requête SPARQL Update exécutée. Une intervention datée dans le futur est
  affichée comme planifiée.
- Backend :
  - `GET /api/maintenance/equipements?category=&q=&horizon=`
  - `GET /api/maintenance/equipements/{id}`
  - `GET /api/maintenance/interventions?kind=&q=`
  - `GET /api/maintenance/interventions/{id}`
  - `POST /api/maintenance/interventions` (`INSERT DATA`)
  - `PUT /api/maintenance/interventions/{id}` (`DELETE … INSERT … WHERE`)
  - `DELETE /api/maintenance/interventions/{id}` (`DELETE WHERE`)
- Code : `frontend/src/features/maintenance/` et
  `backend/app/features/maintenance/` ; tests : `backend/tests/test_maintenance.py`.
