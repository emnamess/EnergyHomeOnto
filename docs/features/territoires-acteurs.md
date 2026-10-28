# Feature 5 — Territoires et acteurs

Cette feature verticale est construite avec son interface React, son backend
FastAPI et ses requêtes SPARQL dédiées.

- Ontologie : `Zone`, `Quartier`, `Ville`, `Personne`, `Acteur` et
  `GestionnaireReseau`.
- Frontend : consultation des territoires et acteurs, avec détail des éléments
  situés dans un territoire ou des équipements gérés par un acteur.
- Backend : `GET /api/territoires-acteurs/territoires`,
  `GET /api/territoires-acteurs/territoires/{id}`,
  `GET /api/territoires-acteurs/acteurs` et
  `GET /api/territoires-acteurs/acteurs/{id}`.
- Code : `frontend/src/features/territoires-acteurs/` et
  `backend/app/features/territoires_acteurs/`.
- Contrats : partager le modèle JSON et les changements de vocabulaire via PR.
