# Backend Python

API FastAPI pour EnergyHomeOnto. Elle interroge Apache Jena Fuseki par SPARQL.

## Démarrage local

Depuis `backend/` :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

L’API est disponible sur `http://localhost:8000` et sa documentation interactive
sur `http://localhost:8000/docs`.

`FUSEKI_QUERY_URL` définit l’endpoint SPARQL ; la valeur locale par défaut est
`http://localhost:3030/energyhome/query`.

## Organisation

- `app/features/<feature>/` : code backend de chaque feature individuelle.
- `app/shared/recherche/` : module de recherche intelligente commun aux cinq
  membres, incluant le moteur local français vers SPARQL et l’accès Fuseki.
- `app/main.py` : assemblage de l’application et routes communes.
