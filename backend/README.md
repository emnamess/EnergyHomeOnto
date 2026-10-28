# Backend Python

API FastAPI pour EnergyHomeOnto. L’ontologie `../energyhomeonto.owx` est lue avec
owlready2, enrichie par le raisonneur OWL RL (owlrl) et interrogée en SPARQL avec
rdflib : aucun serveur Fuseki ni Docker n’est nécessaire. Guide complet : `../README.md`.

## Démarrage avec uv

Depuis `backend/` :

```powershell
uv venv
uv pip install -r requirements-dev.txt
uv run uvicorn app.main:app --reload --port 8000
```

L’API est disponible sur `http://localhost:8000` et sa documentation interactive
sur `http://localhost:8000/docs`.

## Tests

```powershell
uv run pytest
```

Les tests de `tests/` appellent l’API avec `TestClient` sur le graphe RDF local.

## Organisation

- `app/features/<feature>/` : code backend de chaque feature individuelle.
- `app/shared/recherche/` : module NLP commun (spaCy) qui transforme une phrase
  française en requête SPARQL.
- `app/shared/rdf_store.py` : chargement de l’ontologie, raisonnement, `query()`,
  `ask()` et `update()`.
- `app/shared/sparql.py` : préfixes et échappement des valeurs.
- `../data/journal-crud.rq` : modifications CRUD locales, rejouées au démarrage.
