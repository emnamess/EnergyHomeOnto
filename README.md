# EnergyHomeOnto — application web sémantique

Application d’exploration et de gestion d’un réseau énergétique intelligent
(habitat, production, stockage, réseau, territoires) construite sur l’ontologie
OWL `energyhomeonto.owx`.

| Couche | Technologies |
| --- | --- |
| Ontologie | OWL 2 conçue dans Protégé (`energyhomeonto.owx`) |
| Données et raisonnement | owlready2 (lecture OWL/XML), rdflib (graphe RDF + SPARQL 1.1), owlrl (raisonneur OWL RL) |
| Backend | Python 3.11+, FastAPI |
| NLP / TALN | spaCy 3.8 avec le modèle français `fr_core_news_sm` |
| Frontend | React 19, TypeScript, Vite |

Aucune API de LLM (OpenAI, Gemini…) n’est utilisée. Aucun Docker, Fuseki ou Java n’est nécessaire.

---

## 1. Démarrage rapide

Prérequis : Python 3.11 ou 3.12, [uv](https://docs.astral.sh/uv/), Node.js 20+ avec npm, Git.

```powershell
git clone https://github.com/emnamess/EnergyHomeOnto.git
cd EnergyHomeOnto
```

**Terminal 1 — backend** (le premier `uv pip install` télécharge spaCy et son modèle français, compter quelques minutes) :

```powershell
cd backend
uv venv
uv pip install -r requirements-dev.txt
uv run uvicorn app.main:app --reload --port 8000
```

Au démarrage, l’API charge l’ontologie, exécute le raisonneur (≈ 2 s) et le modèle spaCy.
Vérifier sur <http://localhost:8000/api/health> puis explorer les routes sur <http://localhost:8000/docs>.

**Terminal 2 — frontend** :

```powershell
cd frontend
npm install
npm run dev
```

Ouvrir <http://localhost:5173>. L’application s’ouvre sur le **tableau de bord** (chiffres de l’ontologie,
ce que le raisonneur a déduit, scénario de démonstration) ; la barre latérale mène aux autres pages.

**Tests** (depuis `backend/`) : `uv run pytest`. Ils doivent tous passer avant chaque pull request.

> Si la page affiche « Impossible de charger… », le backend n’est pas lancé ou a
> planté : regarder le terminal 1.

---

## 2. Conformité au cahier des charges

| Exigence de la validation | Où la trouver |
| --- | --- |
| Ontologie liée à la thématique | `energyhomeonto.owx` : 45 classes, 13 propriétés d’objet, 43 propriétés de données, 120 individus (Tunis, Ariana, Sfax, Sousse) |
| ObjectProperty, DataProperty, individus, axiomes | Domaines/portées, sous-classes, classes disjointes, classes définies (`MaisonAutonome ≡ Maison ⊓ ∃possede.PanneauSolaire`…), propriétés inverses, transitives et fonctionnelles, restrictions |
| Axiomes réellement exploités | Raisonneur OWL RL (`backend/app/shared/rdf_store.py`), complété pour les classes définies par un seuil numérique : les requêtes portent sur le graphe inféré (2 142 → ~6 400 triplets). Le tableau de bord liste les 10 classes définies et leurs individus déduits |
| Interfaces front et back | React (`frontend/`) + FastAPI (`backend/`) |
| Communication front ↔ back | API REST JSON, proxy Vite `/api` → port 8000 |
| SPARQL : lecture | `SELECT` dans chaque `queries.py` |
| SPARQL : CRUD | `INSERT DATA`, `DELETE … INSERT … WHERE`, `DELETE WHERE` (feature 5 : acteurs) |
| SPARQL : filtrage et recherche | `FILTER(CONTAINS(...))`, `VALUES`, filtres numériques générés par la recherche |
| Module NLP question → SPARQL | `backend/app/shared/recherche/` avec spaCy (voir § 5) |

**État des features** : la feature 5 (territoires et acteurs) et la recherche
intelligente sont terminées. Les features 1 à 4 sont à développer par leurs
responsables en suivant le § 6.

---

## 3. Architecture

```text
energyhomeonto.owx (Protégé)
        │  owlready2 : lecture OWL/XML
        ▼
graphe asserté (rdflib) ◄── data/journal-crud.rq : modifications CRUD rejouées au démarrage
        │  owlrl : raisonnement OWL RL + classes à seuil numérique (GrosConsommateur…)
        ▼
graphe inféré ──► requêtes SPARQL (rdflib)
        ▲
FastAPI : features/<feature>/ et shared/recherche/  ◄── HTTP/JSON ──  React (Vite)
```

```text
backend/app/
  main.py                      enregistrement des routeurs, préchargement au démarrage
  shared/rdf_store.py          query(), ask(), update() : point d’accès unique au graphe
  shared/sparql.py             PREFIXES, string(), number(), most_specific_kind()
  shared/recherche/            module NLP commun (question → SPARQL)
  features/territoires_acteurs/  exemple complet de feature (lecture, filtres, CRUD)
  features/<feature>/          à remplir par chaque membre
backend/tests/                 tests pytest de l’API
frontend/src/
  App.tsx                      routage par #hash
  shared/Layout.tsx            barre latérale (SECTIONS), en-tête de page, état de l’API
  shared/tableau-de-bord/      page d’accueil (backend : app/shared/tableau_de_bord.py)
  shared/recherche-intelligente/  page de recherche
  features/territoires-acteurs/   exemple complet de page
```

**Points importants**

- `energyhomeonto.owx` est **la seule source** de l’ontologie et des individus.
  On le modifie dans Protégé, puis on redémarre le backend (ou on laisse `--reload` le faire).
- Les écritures faites depuis l’application (CRUD) sont ajoutées à
  `data/journal-crud.rq` (ignoré par Git) et rejouées à chaque démarrage. Elles
  survivent donc aux modifications de l’ontologie dans Protégé. Supprimer ce
  fichier remet les données à l’état de l’ontologie.
- Les lectures se font sur le graphe **inféré** : une maison déclarée `:Maison` qui
  possède un panneau solaire apparaît aussi comme `:MaisonAutonome`, `estProprietaireDe`
  est déduit de `appartientA`, `estSitueDans` est transitif, etc.

---

## 4. Modifier l’ontologie

1. Ouvrir `energyhomeonto.owx` dans Protégé.
2. Garder l’espace de noms `http://www.example.org/energyhomeonto#` et ne pas
   renommer les classes ou propriétés déjà utilisées par les autres features
   sans prévenir le groupe.
3. Donner un `:nom` aux individus que l’interface doit afficher (sinon c’est l’identifiant qui s’affiche).
4. Lancer **Reasoner → HermiT → Start reasoner** pour vérifier que l’ontologie est cohérente.
5. Enregistrer **au format OWL/XML** (même fichier), redémarrer le backend, lancer `uv run pytest`.
6. Les nouvelles classes et propriétés sont reconnues automatiquement par la recherche
   intelligente (le lexique est construit depuis l’ontologie).

---

## 5. Recherche intelligente (NLP / TALN)

Route : `POST /api/search` avec `{"query": "..."}`. Réponse : interprétation, requête
SPARQL générée, résultats et analyse spaCy (affichée dans l’interface).

### Chaîne de traitement

| Étape | Outil | Fichier |
| --- | --- | --- |
| 1. Tokenisation, lemmatisation, étiquetage morpho-syntaxique (POS), analyse en dépendances | spaCy `fr_core_news_sm` | `analyse.py` |
| 2. Lexique construit automatiquement depuis l’ontologie (classes, propriétés, individus, synonymes) | rdflib + SPARQL | `vocabulaire.py` |
| 3. Reconnaissance des entités de l’ontologie dans la phrase (sur les lemmes, multi-mots) | spaCy (lemmes) | `analyse.py` |
| 4. Détection de la négation, des comparaisons (« supérieur à », « entre … et … »), des superlatifs, du comptage | spaCy (tokens, nombres) | `analyse.py` |
| 5. Choix de la relation entre deux concepts : domaines/portées OWL + verbe de la phrase (lemme et arbre de dépendances) | spaCy + ontologie | `interpreter.py` |
| 6. Génération puis exécution SPARQL sur le graphe inféré | rdflib | `interpreter.py`, `service.py` |

### Exemples de questions comprises

- « Liste les maisons autonomes qui possèdent un panneau solaire » (classe définie, inférée)
- « maisons sans panneau solaire », « maisons non autonomes » (négation → `FILTER NOT EXISTS`)
- « lignes gérées par la STEG » (verbe *gérer* → `estGerePar`, inverse inféré)
- « Combien de maisons à Tunis ? » (comptage + `estSitueDans` transitif)
- « batteries avec une capacité supérieure à 20 », « sources d’énergie avec une puissance entre 5 et 50 »
- « quel est le panneau solaire le plus puissant » (superlatif → `ORDER BY DESC … LIMIT 1`)
- « Dans quel quartier se trouve la maison 1 ? », « maisons de Sarra », « Ahmed » (description d’un individu)

### Étendre la recherche pour sa feature

- **Nouveau mot pour un concept** (« habitation » → `Maison`) : ajouter une entrée dans
  `SYNONYMES` (`vocabulaire.py`). Écrire les formes en minuscules, sans accents, au singulier.
- **Nouveau verbe** (« raccorder » → `relie`) : ajouter le lemme sans accents dans
  `INDICES` (`interpreter.py`).
- **Deux propriétés possibles, mauvais choix** : ajuster l’ordre de `PRIORITE` (`interpreter.py`).
- Ajouter chaque nouvelle question dans `test_search` (`backend/tests/test_api.py`).

Pour la présentation, citer : **spaCy** (tokenisation, lemmatisation, POS, dépendances,
modèle `fr_core_news_sm`), **rdflib** (SPARQL), **owlrl** (raisonnement OWL RL),
**owlready2** (lecture OWL/XML).

---

## 6. Guide : développer sa feature (features 1 à 4)

La feature 5 (`territoires_acteurs`) sert de modèle complet : la copier est le plus
simple. Exemple ci-dessous pour la feature **Stockage** ; remplacer par `batiments`,
`production` ou `reseau`.

### Étape 1 — Créer sa branche

```powershell
git checkout main
git pull
git checkout -b feature/stockage
```

### Étape 2 — Écrire les requêtes SPARQL : `backend/app/features/stockage/queries.py`

```python
from app.shared.sparql import PREFIXES, most_specific_kind, number, string


def storage_list(min_capacity: float | None = None, text: str | None = None) -> str:
    filters = ""
    if min_capacity is not None:
        filters += f"FILTER(?capacity >= {number(min_capacity)})\n"
    if text:
        filters += f"FILTER(CONTAINS(LCASE(STR(?storage)), LCASE({string(text)})))\n"
    return PREFIXES + f"""
SELECT ?storage ?capacity ?charge (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds) WHERE {{
  ?storage a :Stockage .
  OPTIONAL {{ ?storage :capacite ?capacity }}
  OPTIONAL {{ ?storage :niveauCharge ?charge }}
  {most_specific_kind("storage")}
  {filters}
}}
GROUP BY ?storage ?capacity ?charge
ORDER BY DESC(?capacity)
"""
```

**Règles de sécurité** (obligatoires) :

- Toute valeur saisie par l’utilisateur passe par `string()` ou `number()` (`app/shared/sparql.py`) :
  jamais de f-string directe avec du texte utilisateur.
- Tout identifiant reçu dans une URL est validé avec `is_identifier()` avant d’être mis dans une requête.

### Étape 3 — Ajouter les écritures (CRUD)

Modèle à copier : `create_actor`, `update_actor`, `delete_actor` dans
`features/territoires_acteurs/queries.py` et `service.py`.

| Opération | SPARQL Update | Exécution |
| --- | --- | --- |
| Créer | `INSERT DATA { :id a :Classe, owl:NamedIndividual ; :prop valeur . }` | `update(sparql)` |
| Modifier | `DELETE { :id :prop ?ancien } INSERT { :id :prop nouvelle } WHERE { OPTIONAL { :id :prop ?ancien } }` | `update(sparql)` |
| Supprimer | `DELETE WHERE { :id ?p ?o } ; DELETE WHERE { ?s ?p :id }` | `update(sparql)` |

`update()` applique la requête, l’enregistre dans le journal et relance le raisonneur.

### Étape 4 — Schémas, service et routes

- `schemas.py` : modèles Pydantic des réponses et des formulaires (voir `ActorInput`, `Mutation`).
- `service.py` : appelle `query()` / `ask()` / `update()` de `app.shared.rdf_store` et
  transforme les lignes en schémas. Lever `HTTPException(404)` si l’élément n’existe pas.
- `router.py` :

```python
from fastapi import APIRouter
from app.features.stockage import service
from app.features.stockage.schemas import Storage

router = APIRouter(prefix="/stockage", tags=["Stockage"])


@router.get("/", response_model=list[Storage])
def storages(min_capacity: float | None = None, q: str | None = None) -> list[Storage]:
    return service.list_storages(min_capacity, q)
```

- Enregistrer le routeur dans `backend/app/main.py` :

```python
from app.features.stockage.router import router as storage_router
app.include_router(storage_router, prefix="/api")
```

Vérifier dans <http://localhost:8000/docs> que les routes répondent.

### Étape 5 — Tests : `backend/tests/test_stockage.py`

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_storages_filtered_by_capacity():
    ids = [s["id"] for s in client.get("/api/stockage/", params={"min_capacity": 100}).json()]
    assert ids == ["stockageH2_1", "batterie3"]
```

Les tests écrivent dans un journal temporaire (`tests/conftest.py`) : ils ne touchent pas à vos données.

### Étape 6 — Page React : `frontend/src/features/stockage/StoragePage.tsx`

Copier la structure de `features/territoires-acteurs/TerritoriesActorsPage.tsx`
(liste + filtres + détail + formulaire). Appeler l’API avec des chemins relatifs
(`fetch('/api/stockage/')`) : le proxy Vite redirige vers FastAPI.

Puis déclarer la page :

1. `frontend/src/shared/Layout.tsx` : dans `SECTIONS`, passer `ready: true` sur l’entrée `#/stockage`
   (elle est déjà présente, grisée « à venir »).
2. `frontend/src/App.tsx` : ajouter
   `if (route === '#/stockage') return <Layout current={route}><StoragePage /></Layout>`.
3. Commencer la page par `<PageHeader eyebrow="FEATURE 3" title="Stockage">description</PageHeader>`
   (importé de `../../shared/Layout`) : la barre latérale est fournie par `Layout`.
4. Réutiliser les classes CSS existantes de `style.css` (`card`, `filters`, `explorer`, `list-item`,
   `metrics`, `actor-form`…) et les couleurs déclarées en variables dans `:root`.
5. Optionnel : ajouter une étape au scénario de démonstration (`SCENARIO` dans
   `shared/tableau-de-bord/DashboardPage.tsx`).

Vérifier : `npx tsc -b` (aucune erreur) puis tester dans le navigateur.

### Étape 7 — Enrichir la recherche intelligente

Ajouter les synonymes et verbes de votre domaine (§ 5) et 2 ou 3 questions dans `test_search`.

### Étape 8 — Pull request

```powershell
cd backend; uv run pytest; cd ..
git add -A
git commit -m "Feature stockage : liste, filtres, CRUD et page React"
git push -u origin feature/stockage
```

Ouvrir la pull request vers `main` sur GitHub en décrivant les routes, les requêtes
SPARQL et des captures de l’interface. Un autre membre relit avant la fusion.

### Checklist de la feature avant la PR

- [ ] Au moins une liste avec **filtres** traduits en SPARQL (`FILTER`, `VALUES`)
- [ ] Une page de **détail**
- [ ] **CRUD** complet sur au moins un type d’individu (`INSERT DATA`, `DELETE/INSERT WHERE`, `DELETE WHERE`)
- [ ] Une requête qui exploite une **inférence** (classe définie, inverse, transitivité…)
- [ ] Valeurs utilisateur échappées avec `string()` / `number()`
- [ ] Tests pytest qui passent, `npx tsc -b` sans erreur
- [ ] Synonymes / verbes ajoutés à la recherche intelligente avec des tests

---

## 7. Règles Git de l’équipe

- Une branche par feature (`feature/<nom>`), jamais de commit direct sur `main`.
- `git pull` sur `main` avant de créer sa branche ; `git merge main` dans sa branche si `main` a avancé.
- Les fichiers partagés (`main.py`, `App.tsx`, `Layout.tsx`, `style.css`, `vocabulaire.py`,
  `interpreter.py`, l’ontologie) se modifient en petites retouches : prévenir le groupe pour éviter les conflits.
- Si l’historique d’une branche a été réécrit (`git push --force`), **ne pas** cliquer sur
  « Synchroniser les modifications » dans VS Code : utiliser
  `git fetch` puis `git reset --hard origin/<branche>`.
- Ne jamais committer `backend/.venv`, `frontend/node_modules` ni `data/journal-crud.rq` (déjà dans `.gitignore`).

---

## 8. Dépannage

| Symptôme | Solution |
| --- | --- |
| `ModuleNotFoundError` au démarrage du backend | `uv pip install -r requirements-dev.txt` dans `backend/` |
| `Can't find model 'fr_core_news_sm'` | même commande : le modèle est listé dans `requirements.txt` |
| Données incohérentes après des essais CRUD | arrêter le backend, supprimer `data/journal-crud.rq`, relancer |
| La recherche ne reconnaît pas un mot | ajouter un synonyme (§ 5) ; vérifier l’onglet « Tokens, lemmes et dépendances » dans l’interface |
| Port 8000 ou 5173 déjà utilisé | un autre terminal fait déjà tourner le serveur : le fermer ou réutiliser celui-ci |
