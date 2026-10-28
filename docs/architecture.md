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
                                               rdflib / energyhomeonto.ttl
```

## Pull requests

Chaque élève travaille sur une branche de feature et ouvre une pull request vers
`main`. La PR décrit l’interface, les routes REST et les requêtes SPARQL livrées.
Un autre élève relit la PR avant fusion. Les cinq membres contribuent également
au module partagé de recherche intelligente ; ses changements sont coordonnés et
intégrés par PR vers `main`.

## Recherche intelligente

`POST /api/search` reçoit `{ "query": "..." }`. L’analyseur local comprend la
phrase par des règles codées dans le projet, compose un patron SPARQL depuis les
classes et propriétés connues, puis l’exécute sur le graphe RDF local. Aucun
service d’IA distant n’est utilisé.
