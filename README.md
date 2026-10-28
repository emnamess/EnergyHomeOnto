# EnergyHomeOnto — application web sémantique

Application de gestion et d’exploration d’un habitat énergétique à partir de
l’ontologie `energyhomeonto.owx`. Le backend Python exécute les requêtes SPARQL
localement avec `rdflib` sur le graphe RDF `data/energyhomeonto.ttl`.

## Technologies

- Frontend : React, TypeScript et Vite
- Backend : Python 3.12, FastAPI et `rdflib`
- Données : OWL/XML comme source et Turtle (`.ttl`) à l’exécution
- Recherche intelligente : règles locales français → SPARQL, sans API IA externe

## Cinq features individuelles

| Feature | Frontend | Backend et SPARQL |
| --- | --- | --- |
| 1. Bâtiments et habitats | Liste, détail et filtres de bâtiments. | API et requêtes sur les bâtiments, équipements et consommation. |
| 2. Production énergétique | Catalogue des sources et filtres par type. | API et requêtes sur panneaux, éoliennes, centrales et puissance. |
| 3. Stockage | Capacités et niveaux de charge. | API et requêtes sur batteries et autres stockages. |
| 4. Réseau énergétique | Lignes, postes et connexions. | API et requêtes sur le réseau électrique. |
| 5. Territoires et acteurs | Villes, quartiers, personnes et gestionnaires. | API et requêtes sur les zones, acteurs et équipements gérés. |

Chaque membre développe sa feature de manière verticale dans :

```text
frontend/src/features/<feature>/
backend/app/features/<feature>/
```

La recherche intelligente est un module commun aux cinq membres :

```text
frontend/src/shared/recherche-intelligente/
backend/app/shared/recherche/
backend/app/shared/rdf_store.py
```

Les branches `feature/<nom>` sont intégrées à `main` avec une pull request qui
présente l’interface, les routes API et les requêtes SPARQL livrées.

## Démarrage local avec uv

Prérequis : Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js avec npm.
Docker, Fuseki et Java ne sont pas nécessaires.

Dans une première fenêtre PowerShell :

```powershell
cd backend
uv venv
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload --port 8000
```

L’API est disponible sur `http://localhost:8000` et sa documentation interactive
sur `http://localhost:8000/docs`.

Dans une deuxième fenêtre :

```powershell
cd frontend
npm install
npm run dev
```

Ouvrir ensuite `http://localhost:5173`.

## Données RDF et SPARQL

`data/energyhomeonto.ttl` est chargé une seule fois au démarrage par `rdflib`.
Il contient un jeu de données opérationnel pour les fonctionnalités du projet.
Pour charger l’ensemble de votre ontologie, exportez `energyhomeonto.owx` depuis
Protégé au format Turtle, puis complétez ou remplacez ce fichier.

## Recherche intelligente locale

La recherche intelligente analyse la phrase, identifie les concepts connus et
génère une requête SPARQL contrôlée. Exemple :

```text
Liste les maisons autonomes qui possèdent un panneau solaire
```

Le moteur produit la requête puis l’exécute directement sur le graphe RDF local.
