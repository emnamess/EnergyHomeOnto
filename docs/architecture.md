# Architecture initiale

```text
React / TypeScript
       │ HTTP/JSON
       ▼
Spring Boot REST API ─── moteur local français → SPARQL
       │ SPARQL Protocol
       ▼
Apache Jena Fuseki (dataset RDF energyhome)
       ▲
       └── ontologie OWL/XML + données RDF
```

## Responsabilités

- Le navigateur envoie soit des filtres structurés, soit une phrase en français.
- Le backend valide la demande. Pour une phrase, il appelle le moteur de règles
  local ; il n’appelle aucun fournisseur d’IA distant.
- Le moteur produit uniquement des patrons SPARQL autorisés à partir des classes
  et propriétés connues. Les valeurs utilisateur sont liées comme paramètres,
  jamais concaténées sans contrôle dans une requête.
- Le backend exécute le SPARQL sur le dataset Fuseki puis renvoie des résultats
  JSON au frontend.
- L’ontologie définit le vocabulaire partagé et les données RDF fournissent les
  individus interrogés.

## Contrat REST proposé

`POST /api/search`

```json
{ "query": "Liste les maisons autonomes qui possèdent une batterie" }
```

Réponse indicative :

```json
{
  "interpretation": "Maisons autonomes possédant une batterie",
  "sparql": "SELECT ...",
  "results": []
}
```

Le backend doit aussi exposer `GET /api/health`. Les noms et formats sont des
propositions de départ à valider ensemble avant l’implémentation.
