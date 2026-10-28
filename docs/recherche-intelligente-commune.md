# Module commun — Recherche intelligente

La recherche intelligente est transverse aux cinq features, ne constitue pas une
feature individuelle et n’est pas attribuée à un seul élève. Les cinq membres
contribuent au frontend, au backend et à la génération/exécution SPARQL.

- Frontend commun : barre de recherche accessible depuis les cinq features,
  interprétation, requête générée et résultats.
- Backend commun : analyseur local français → SPARQL et patrons validés.
- Exécution : `rdflib` interroge localement `data/energyhomeonto.ttl`.
- Le traitement est codé dans le projet et n’appelle aucune API d’IA externe.
- Frontend : `frontend/src/shared/recherche-intelligente/`.
- Backend : `backend/app/shared/recherche/` et `backend/app/shared/rdf_store.py`.
- Toute modification passe par une PR vers `main`, relue et coordonnée entre les
  cinq membres.
