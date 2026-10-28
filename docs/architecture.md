# Architecture en features verticales

Chaque feature porte son parcours complet : composants React, endpoint FastAPI,
service métier et requêtes SPARQL. Les features partagent le vocabulaire OWL,
le graphe RDF local et l’application hôte ; elles ne sont pas découpées par couche
technique.

```text
Frontend React                         Backend Python / FastAPI
features/batiments  ── HTTP/JSON ──►  features/batiments ── SPARQL ──┐
features/production ── HTTP/JSON ──►  features/production ─ SPARQL ─┤
features/stockage   ── HTTP/JSON ──►  features/stockage ─── SPARQL ─┤
features/reseau     ── HTTP/JSON ──►  features/reseau ───── SPARQL ─┤
features/territoires── HTTP/JSON ──►  features/territoires ─ SPARQL ─┤
shared/recherche    ── HTTP/JSON ──►  shared/recherche ───── SPARQL ─┤
                                                                    ▼
                              rdflib + owlrl (graphe inféré) ◄── owlready2 ◄── energyhomeonto.owx
```

## Pull requests

Chaque élève travaille sur une branche de feature et ouvre une pull request vers
`main`. La PR décrit l’interface, les routes REST et les requêtes SPARQL livrées.
Un autre élève relit la PR avant fusion. Les cinq membres contribuent également
au module partagé de recherche intelligente ; ses changements sont coordonnés et
intégrés par PR vers `main`.

## Recherche intelligente

`POST /api/search` reçoit `{ "query": "..." }`. spaCy (`fr_core_news_sm`)
analyse la phrase (lemmes, catégories, dépendances), les termes de l’ontologie y
sont reconnus, puis une requête SPARQL est composée à partir des domaines et
portées des propriétés et exécutée sur le graphe inféré. Aucun service d’IA
distant n’est utilisé. Détails : `README.md` racine, § 5.
