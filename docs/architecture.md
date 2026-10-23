# Architecture en features verticales

Chaque feature porte son parcours complet : composants React, endpoint REST,
service métier et requêtes SPARQL. Les features partagent le vocabulaire OWL,
Fuseki et l’application hôte ; elles ne sont pas découpées par couche technique.

```text
Frontend React                         Backend Python / FastAPI
features/batiments  ── HTTP/JSON ──►  features/batiments ── SPARQL ──┐
features/production  ── HTTP/JSON ──►  features/production ─ SPARQL ─┤
features/stockage    ── HTTP/JSON ──►  features/stockage ─── SPARQL ─┤
features/reseau      ── HTTP/JSON ──►  features/reseau ───── SPARQL ─┤
features/territoires ── HTTP/JSON ──►  features/territoires ─ SPARQL ┤
shared/recherche     ── HTTP/JSON ──►  shared/recherche ───── SPARQL ┤
                                                                    ▼
                                                 Apache Jena Fuseki / dataset
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
classes/propriétés connues, puis interroge Fuseki. Aucun service d’IA distant
n’est utilisé.
