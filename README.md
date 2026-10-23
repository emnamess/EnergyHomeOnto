# EnergyHomeOnto — application web sémantique

Application de gestion et d’exploration d’un habitat énergétique à partir de
l’ontologie OWL/XML `energyhomeonto.owx`. Le travail est réparti en **cinq
features verticales** : chaque feature possède son interface frontend, son API et
ses requêtes SPARQL. Les élèves livrent leur feature dans une pull request vers
`main`.

## Technologies

- **Frontend :** React, TypeScript et Vite
- **Backend :** Python 3.12, FastAPI, HTTPX et SPARQL
- **Ontologie / données :** OWL/XML et RDF
- **Endpoint SPARQL :** Apache Jena Fuseki
- **Recherche intelligente :** moteur local de règles NLP → SPARQL, codé dans le
  projet, sans API d’IA externe

## Les cinq features individuelles (un élève responsable par feature)

| Feature | Périmètre métier | Frontend de la feature | Backend et SPARQL de la feature |
| --- | --- | --- | --- |
| 1. Bâtiments et habitats | Maison, maison autonome, bâtiments public/industriel/commercial, consommation et équipement. | Liste, détail, filtres et formulaire de bâtiment. | API bâtiments et requêtes de sélection/détail/filtrage des bâtiments. |
| 2. Production énergétique | Sources d’énergie, panneaux solaires, éoliennes, centrales, puissance et émissions. | Catalogue et détail des sources, filtres par type/puissance. | API sources et requêtes SPARQL sur les sources et leurs propriétés. |
| 3. Stockage | Batteries, autres stockages, capacité et niveau de charge. | Liste et détail des unités de stockage, filtres et indicateurs. | API stockage et requêtes SPARQL sur les unités, capacités et bâtiments alimentés. |
| 4. Réseau énergétique | Lignes électriques, équipements réseau, tension, relations d’alimentation et connexions. | Vue des lignes/équipements et détails des connexions. | API réseau et requêtes SPARQL sur `LigneElectrique`, `relie`, `alimente` et équipements. |
| 5. Territoires et acteurs | Zones, quartiers, villes, personnes et gestionnaires de réseau. | Consultation et filtres par territoire ou acteur. | API dédiée et requêtes SPARQL sur les zones, personnes et gestionnaires. |

Les chemins d’implémentation suivent la même organisation pour que chaque élève
possède toute sa feature :

```text
frontend/src/features/<feature>/   # composants, appels HTTP, styles
backend/app/features/<feature>/
                                  # contrôleur, service métier et SPARQL
frontend/src/shared/recherche-intelligente/ # recherche commune aux cinq features
backend/app/shared/recherche/ # moteur et SPARQL communs
```

Le démarrage fournit le squelette du module **Recherche intelligente commun**.
Les cinq features individuelles ont leur périmètre réservé ; leurs interfaces
et API sont à développer par les élèves concernés.

## Travail en branches et pull requests

1. Chaque élève part de `main` et crée une branche dédiée, par exemple
   `feature/batiments`, `feature/production`, `feature/stockage`,
   `feature/reseau` ou `feature/territoires-acteurs`.
2. Il implémente frontend, backend et SPARQL dans le dossier de sa feature.
3. Avant de coder une route ou un modèle partagé, l’élève documente son contrat
   dans le README de la feature et le coordonne avec le groupe.
4. Il ouvre une **pull request vers `main`** avec résumé, captures ou exemple
   d’appel API, et points d’intégration. Un autre élève relit la PR.
5. Après correction et validation par l’équipe, la PR est fusionnée dans `main`.
   Les conflits sur l’ontologie, la configuration ou les contrats se règlent
   ensemble avant la fusion.

`main` contient l’application assemblée et doit rester lançable. En plus de leurs
features, les cinq membres contribuent ensemble au module transversal de
recherche intelligente. Il offre une barre de recherche commune aux cinq écrans,
un moteur local français → SPARQL et une API partagée. Les contributions à ce
module passent aussi par des PR vers `main` et sont relues par le groupe.

## Arborescence

```text
EnergyHomeOnto/
├── energyhomeonto.owx
├── frontend/src/features/
│   ├── batiments/
│   ├── production/
│   ├── stockage/
│   ├── reseau/
│   └── territoires-acteurs/
├── frontend/src/shared/recherche-intelligente/
├── backend/app/features/
│   ├── batiments/
│   ├── production/
│   ├── stockage/
│   ├── reseau/
│   └── territoires-acteurs/
├── backend/app/shared/recherche/
├── data/
├── docs/
└── docker-compose.yml
```

## Démarrage local

Prérequis : Python 3.12, Node.js avec npm et Docker Compose.

1. Fuseki : `docker compose up -d fuseki` (interface Fuseki :
   `http://localhost:3030`).
2. Créer le dataset `energyhome` et y charger l’ontologie et les données RDF.
3. API : dans `backend/`, créer un environnement virtuel, installer
   `requirements.txt`, puis lancer `uvicorn app.main:app --reload --port 8000`.
4. Frontend : dans `frontend/`, lancer `npm install`, puis `npm run dev`.

L’API utilise par défaut `http://localhost:3030/energyhome/query` ; remplacer
cette adresse avec `FUSEKI_QUERY_URL` si nécessaire. Sans dataset chargé, la
recherche SPARQL ne peut pas retourner de résultats.

## Module commun : recherche intelligente locale

La recherche intelligente est un module transversal aux cinq features, pas une
feature individuelle. C’est une implémentation logicielle locale, pas un appel
à un service d’IA. Son premier moteur Python normalise la phrase, repère quelques concepts
(batterie, panneau solaire, éolienne et maison autonome), choisit un patron
SPARQL autorisé et l’envoie à Fuseki. Exemple :

```text
« Liste les maisons autonomes qui possèdent un panneau solaire »
```

L’analyseur initial est volontairement limité ; l’élève responsable l’étendra
avec synonymes, propriétés, filtres et règles de compréhension supplémentaires.

## Ontologie

L’ontologie existante contient déjà des concepts résidentiels, de production,
stockage et réseau. La classe `Vehicule` n’est pas présente dans le fichier au
démarrage ; une recherche de véhicules nécessiterait une évolution de l’ontologie
et des données.
