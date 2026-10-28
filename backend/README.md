# Backend Python

API FastAPI pour EnergyHomeOnto. Les requêtes SPARQL sont exécutées localement
par `rdflib` sur `data/energyhomeonto.ttl` : aucun serveur Fuseki ni Docker n’est
nécessaire.

## Démarrage avec uv

Depuis `backend/` :

```powershell
uv venv
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload --port 8000
```

L’API est disponible sur `http://localhost:8000` et sa documentation interactive
sur `http://localhost:8000/docs`.

## Organisation

- `app/features/<feature>/` : code backend de chaque feature individuelle.
- `app/shared/recherche/` : module commun qui transforme une phrase française en
  requête SPARQL locale.
- `app/shared/rdf_store.py` : chargement unique du graphe Turtle et exécution
  des requêtes.
- `../data/energyhomeonto.ttl` : données RDF utilisées à l’exécution.
