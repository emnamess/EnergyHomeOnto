# Données RDF

`energyhomeonto.ttl` est le graphe RDF local chargé par FastAPI avec `rdflib`.
Il contient les données nécessaires aux cinq features et fonctionne sans Fuseki,
Docker ou service externe.

Le fichier source `energyhomeonto.owx` est une ontologie OWL/XML. Pour enrichir
le graphe avec toutes les données de Protégé, exporter l’ontologie au format
Turtle puis remplacer ou compléter `energyhomeonto.ttl`.
