# Feature Production — guide de soutenance

La feature 2 (Production) est terminée. Ce guide explique comment la lancer, ce qu’elle
fait, comment elle est construite et comment la présenter en 5 minutes. Le moment fort :
on installe un panneau solaire sur une maison et **le raisonneur OWL la classe
automatiquement « maison autonome »**, sans aucune règle écrite à la main.

---

## 1. Récupérer et lancer le projet

Prérequis : Python 3.11 ou 3.12, [uv](https://docs.astral.sh/uv/), Node.js 20+, Git.

```powershell
git clone https://github.com/emnamess/EnergyHomeOnto.git
cd EnergyHomeOnto
```

> Si la pull request `feature/production` n’est pas encore fusionnée dans `main`,
> fais en plus : `git checkout feature/production`.

**Terminal 1 — backend** (le premier `uv pip install` télécharge spaCy, compter quelques minutes) :

```powershell
cd backend
uv venv
uv pip install -r requirements-dev.txt
uv run uvicorn app.main:app --reload --port 8000
```

Attendre `Application startup complete.` (quelques secondes : chargement de l’ontologie,
raisonnement, modèle spaCy).

**Terminal 2 — frontend** :

```powershell
cd frontend
npm install
npm run dev
```

Ouvrir <http://localhost:5173>, puis **Production** dans la barre latérale.

Vérifier que tout marche : `uv run pytest tests/test_production.py tests/test_scenario.py`
depuis `backend/` (tous les tests doivent passer).

---

## 2. La feature en bref

La page Production gère les **sources d’énergie** : panneaux solaires, éoliennes,
centrales hydrauliques, centrales thermiques et groupes électrogènes.

| Zone de la page | Ce qu’elle montre |
| --- | --- |
| Tuiles | 23 sources, 1 122,2 kW installés, 6 091 MWh par an, 17,9 % de production renouvelable, 423 g CO₂/kWh en moyenne |
| Graphique | Production annuelle par type de source, en vert les renouvelables, en brun les fossiles |
| Filtres | Recherche par nom, type, renouvelable / non renouvelable, puissance minimale |
| Tableau | Nom, type, puissance, production, émissions, nombre de bâtiments alimentés |
| Panneau de détail (clic sur une ligne) | Caractéristiques, classes déduites par le raisonneur, bâtiment sur lequel la source est installée, bâtiments alimentés, stockages rechargés, zone |
| Formulaire | Créer ou modifier une source ; les champs techniques changent selon le type (surface et inclinaison d’un panneau, rotor d’une éolienne, combustible d’une centrale thermique…) |

À noter : la production est dominée par la centrale thermique de Radès (3 200 MWh), d’où
une part renouvelable de seulement 17,9 % : c’est un argument pour le scénario.

---

## 3. Ce que l’ontologie apporte

Le fichier `energyhomeonto.owx` (Protégé) est la source unique des données. Au démarrage,
le raisonneur **OWL RL** (bibliothèque `owlrl`) déduit de nouveaux faits ; toutes les
requêtes portent sur ce graphe enrichi.

| Élément de l’ontologie | Rôle dans la feature |
| --- | --- |
| `SourceEnergie` et ses sous-classes `PanneauSolaire`, `Eolienne`, `CentraleHydraulique`, `CentraleThermique`, `GroupeElectrogene` | Les 5 types gérés ; ils sont disjoints deux à deux |
| `SourceRenouvelable` / `SourceNonRenouvelable` (disjointes) | Le filtre « renouvelable » utilise l’**inférence par sous-classe** : on ne stocke nulle part qu’une éolienne est renouvelable |
| Classes définies `SourceForte` (≥ 50 kW), `SourceHautRendement` (≥ 80 %), `SourcePolluante` (> 100 g CO₂/kWh) | Affichées comme « classes déduites » dans le détail ; personne ne les saisit |
| `MaisonAutonome ≡ Maison ⊓ ∃possede.PanneauSolaire` | **Le cœur du scénario** : une maison qui possède un panneau devient autonome par déduction |
| Propriétés d’objet `possede`, `alimente`, `stockeDans`, `estSitueDans` | Liens d’une source avec son bâtiment, les bâtiments alimentés, les stockages et sa zone |
| `alimente` / `estAlimentePar` (`owl:inverseOf`) | On écrit `alimente` ; l’inverse est déduit côté bâtiment |
| Propriétés de données `puissance`, `rendement`, `productionAnnuelle`, `emissionCO2`, `surfacePanneau`, `diametreRotor`, `typeCombustible`… | Caractéristiques affichées, filtrées et saisies |

Petite précision technique : `owlrl` ne sait pas évaluer les seuils numériques
(« ≥ 50 kW »). Une étape du projet (`backend/app/shared/rdf_store.py`) lit ces seuils dans
l’ontologie et classe les sources concernées, si bien que `SourceForte`, `SourcePolluante` et `SourceHautRendement` sont bien calculées.

---

## 4. Comment c’est construit

| Fichier | Contenu |
| --- | --- |
| `backend/app/features/production/queries.py` | Toutes les requêtes SPARQL (lecture, filtres, agrégats, CRUD) |
| `backend/app/features/production/service.py` | Logique : contrôles, cohérence avec l’ontologie, appel des requêtes |
| `backend/app/features/production/router.py` | Les routes de l’API (FastAPI) |
| `backend/app/features/production/schemas.py` | Les formats JSON échangés |
| `frontend/src/features/production/ProductionPage.tsx` | La page React |
| `backend/tests/test_production.py` | 27 tests |

| Route | Requête SPARQL |
| --- | --- |
| `GET /api/production/sources?kind=&renewable=&min_power=&q=` | `SELECT` + `FILTER` (puissance, texte) + `?source a :SourceRenouvelable` (inférence) |
| `GET /api/production/indicateurs` | `SELECT` avec `COUNT`, `SUM`, `GROUP BY` par type |
| `GET /api/production/sources/{id}` | `SELECT` du détail + classes déduites + éléments liés |
| `POST /api/production/sources` | `INSERT DATA` (création) |
| `PUT /api/production/sources/{id}` | `DELETE … INSERT … WHERE` (modification) |
| `DELETE /api/production/sources/{id}` | `DELETE WHERE` (suppression) |

Exemple : installer un panneau sur l’Appartement Lafayette exécute (extrait simplifié ; la
requête réelle contient aussi le rendement, l’inclinaison, l’année d’installation…)

```sparql
INSERT DATA {
  :sourceToitureSolaireAppartementLafayette a :PanneauSolaire, owl:NamedIndividual .
  :sourceToitureSolaireAppartementLafayette :nom "Toiture solaire – Appartement Lafayette"^^xsd:string .
  :sourceToitureSolaireAppartementLafayette :puissance "4.0"^^xsd:double .
  :Maison16 :possede :sourceToitureSolaireAppartementLafayette .
  :sourceToitureSolaireAppartementLafayette :alimente :Maison16 .
}
```

Après chaque écriture, le raisonneur est relancé : c’est ce qui fait apparaître
`:Maison16 a :MaisonAutonome`. La requête exécutée s’affiche dans la page (bandeau vert,
« Requête SPARQL Update exécutée »).

Garde-fous à mentionner :

- **Cohérence** : une caractéristique propre à un type est refusée sur un autre (ex. un
  combustible sur une éolienne), car l’ontologie deviendrait incohérente (renouvelable et
  non renouvelable sont disjointes).
- **Intégrité** : une source qui a des interventions de maintenance ne peut pas être supprimée.
- **Sécurité** : toutes les valeurs saisies sont échappées (pas d’injection SPARQL).
- Les modifications sont enregistrées dans `data/journal-crud.rq` et rejouées au démarrage.

---

## 5. Scénario de démonstration (5 minutes)

**Contexte à annoncer** : « Je suis responsable énergie de la ville. Le tableau de bord me
signale des maisons énergivores qui ne produisent pas leur propre énergie. »

1. **Tableau de bord** — Montrer le bandeau « Votre mission » et l’alerte
   **« Maisons énergivores non autonomes »** : Appartement Lafayette (classe G, 30 kWh),
   Dar Médina (classe F), Maison Khezama (classe E).
   *À dire* : « Cette liste n’est pas codée en dur : c’est une requête SPARQL sur le graphe
   déduit. La règle est affichée sous le titre : une maison est autonome si elle possède un
   panneau solaire. »
2. **Recherche intelligente** — Taper « maisons non autonomes avec une consommation
   supérieure à 20 ». Ouvrir « Analyse spaCy » puis « Requête SPARQL générée ».
   *À dire* : « spaCy lemmatise la phrase, reconnaît les concepts de l’ontologie, la
   négation et la comparaison, puis génère le SPARQL : on retrouve les trois mêmes maisons. »
3. **Page Production** — Montrer les tuiles (17,9 % de renouvelable seulement) et le
   graphique ; filtrer « Non renouvelables » ; cliquer sur la centrale de Radès.
   *À dire* : « Les classes déduites `SourceForte`, `SourcePolluante` et
   `SourceNonRenouvelable` viennent du raisonneur, pas de la saisie. »
4. **Agir** — Revenir au tableau de bord, cliquer **« Traiter »** sur l’Appartement Lafayette.
   Le formulaire de Production s’ouvre prérempli (panneau solaire, installé sur la maison,
   qui l’alimente). Cliquer **Enregistrer**, puis ouvrir la requête SPARQL exécutée.
   *À dire* : « C’est un `INSERT DATA`. Je n’ai jamais écrit que la maison est autonome. »
5. **Bilan** — Cliquer « Voir l’effet sur le tableau de bord » : l’Appartement Lafayette a
   disparu de l’alerte et le compteur a baissé.
   *À dire* : « Le raisonneur l’a reclassée `MaisonAutonome` grâce à l’axiome
   d’équivalence : l’ontologie prend la décision. »

Bonus si le temps le permet : modifier la source (changer la puissance → `DELETE/INSERT
WHERE`), puis la supprimer (`DELETE WHERE`) : la maison revient dans l’alerte.

**Pour répéter la démo** : arrêter le backend, supprimer le fichier `data/journal-crud.rq`,
relancer. Toutes les données reviennent à l’état de l’ontologie.

---

## 6. Questions probables du jury

**Où sont les axiomes et à quoi servent-ils ?**
Dans `energyhomeonto.owx`. Ils sont exploités par le raisonneur OWL RL : sous-classes
(renouvelable), classes définies (`MaisonAutonome`, `SourceForte`…), propriétés inverses
(`alimente` / `estAlimentePar`), propriété transitive (`estSitueDans`).

**Pourquoi un raisonneur plutôt que des `if` dans le code ?**
La règle vit dans l’ontologie : si on la change dans Protégé, l’application suit sans
modifier une ligne de code.

**Où est le CRUD ?**
Création `INSERT DATA`, modification `DELETE … INSERT … WHERE`, suppression `DELETE WHERE`,
dans `queries.py`. La requête exécutée est affichée dans l’interface.

**Comment fonctionne le module NLP ? Utilisez-vous une API d’IA ?**
Non, aucune API de LLM. On utilise **spaCy** (modèle `fr_core_news_sm`) : tokenisation,
lemmatisation, étiquetage morpho-syntaxique, analyse en dépendances. Les concepts reconnus
sont ceux de l’ontologie, et la relation entre deux concepts est choisie grâce aux domaines
et portées des propriétés et au verbe de la phrase. Questions de production qui marchent :
« sources fossiles », « quelle source produit le plus », « panneaux installés après 2022 ».

**Comment évitez-vous les données incohérentes ?**
Les propriétés propres à un type sont refusées sur les autres types (domaines de
l’ontologie), le rendement est limité à 0-100 % comme dans l’ontologie, et une source avec
un historique de maintenance ne peut pas être supprimée.

**Quelles technologies ?**
React + TypeScript (Vite) pour l’interface, FastAPI pour l’API, **rdflib** pour SPARQL,
**owlrl** pour le raisonnement, **owlready2** pour lire le fichier Protégé, **spaCy** pour le NLP.

---

## 7. Checklist avant la soutenance

- [ ] Le projet se lance (backend puis frontend) sur ton ordinateur
- [ ] `uv run pytest tests/test_production.py` passe
- [ ] Scénario répété une fois en entier, puis `data/journal-crud.rq` supprimé pour repartir propre
- [ ] Savoir montrer la requête SPARQL générée (recherche) et la requête Update exécutée (Production)
- [ ] Savoir expliquer en une phrase `MaisonAutonome ≡ Maison ⊓ ∃possede.PanneauSolaire`
