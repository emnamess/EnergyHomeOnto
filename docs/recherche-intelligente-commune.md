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
- Toute modification du comportement de recherche s’accompagne d’un cas dans
  `backend/tests/test_api.py`.
- Toute modification passe par une PR vers `main`, relue et coordonnée entre les
  cinq membres.

## Questions comprises

L’analyseur cible les maisons et combine librement :

- l’autonomie : « autonomes », « non autonomes » ;
- les équipements possédés : batterie, panneau solaire, éolienne ;
- la négation devant un équipement : « sans », « pas de », « aucun », « ni ».

Exemples : « maisons avec un panneau solaire sans batterie », « maisons non
autonomes qui n’ont pas d’éolienne ». Une question hors de ce périmètre renvoie
une erreur 400 au lieu d’un résultat approximatif.

Les classes sont reconnues avec `rdfs:subClassOf*` : une `:MaisonAutonome` est
aussi trouvée comme `:Maison` sans être déclarée deux fois dans les données.
