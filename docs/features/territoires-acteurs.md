# Feature 5 — Territoires et acteurs

Cette feature verticale est construite avec son interface React, son backend
FastAPI et ses requêtes SPARQL dédiées. Elle sert de modèle aux autres features.

- Ontologie : `Zone`, `Quartier`, `Ville`, `Personne`, `Acteur` et
  `GestionnaireReseau` ; propriétés `estSitueDans` (transitive), `gere` /
  `estGerePar` et `appartientA` / `estProprietaireDe` (inverses).
- Frontend : territoires et acteurs filtrables par nom et par type, détail des
  éléments situés dans un territoire (avec leur classe inférée), des équipements
  gérés et des bâtiments possédés ; création, modification et suppression
  d’acteurs avec affichage de la requête SPARQL Update exécutée.
- Backend :
  - `GET /api/territoires-acteurs/territoires?kind=&q=`
  - `GET /api/territoires-acteurs/territoires/{id}`
  - `GET /api/territoires-acteurs/acteurs?kind=&q=`
  - `GET /api/territoires-acteurs/acteurs/{id}`
  - `POST /api/territoires-acteurs/acteurs` (`INSERT DATA`)
  - `PUT /api/territoires-acteurs/acteurs/{id}` (`DELETE … INSERT … WHERE`)
  - `DELETE /api/territoires-acteurs/acteurs/{id}` (`DELETE WHERE`)
- Code : `frontend/src/features/territoires-acteurs/` et
  `backend/app/features/territoires_acteurs/`.
