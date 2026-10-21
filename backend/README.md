# Backend

Module Spring Boot. Lancer avec `mvn spring-boot:run` (Java 21 requis). Il expose
`GET /api/health` et `POST /api/search` avec `{ "query": "..." }`. Le moteur
local reconnaît actuellement les recherches de maisons avec batterie, panneau
solaire ou éolienne. Fuseki doit être démarré et contenir le dataset `energyhome`
pour que la recherche renvoie des individus.
