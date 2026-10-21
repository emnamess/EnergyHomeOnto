# EnergyHomeOnto — recherche sémantique énergétique

Projet web sémantique construit autour de l’ontologie OWL `energyhomeonto.owx`.
L’application permettra d’explorer des maisons et leurs équipements énergétiques,
puis de formuler une recherche en langage naturel qui sera transformée en SPARQL
par un moteur local codé dans le projet.

## Technologies retenues

- **Frontend :** React + TypeScript + Vite
- **Backend :** Java 21 + Spring Boot (API REST)
- **Ontologie :** OWL/XML, fichier `energyhomeonto.owx`
- **Base RDF / requêtes :** Apache Jena Fuseki et SPARQL
- **Recherche intelligente :** règles et traitement de texte locaux, sans API IA
  externe, sans clé API et sans envoi des requêtes à un service tiers
- **Lancement local :** Docker Compose pour Fuseki

> « Apache Gena » semble désigner **Apache Jena**. Fuseki est le serveur de
> données RDF de Jena et expose un endpoint SPARQL. Le backend s’y connectera.

## Les cinq modules (un responsable par élève)

| Module | Responsable | Périmètre et livrables |
| --- | --- | --- |
| 1. Ontologie et données | Élève 1 | Faire évoluer `energyhomeonto.owx`, documenter les classes, propriétés et contraintes, préparer des données d’exemple et valider leur cohérence. |
| 2. Backend et SPARQL | Élève 2 | API REST Spring Boot, connexion à Fuseki, exécution des requêtes SPARQL, validation des entrées et format JSON des résultats. |
| 3. Recherche intelligente locale | Élève 3 | Analyseur de phrases en français, détection d’intention, classe/propriétés/valeurs, génération SPARQL et messages en cas de demande non comprise. Aucun appel à une API d’IA. |
| 4. Interface React | Élève 4 | Barre de recherche en langage naturel, filtres, affichage des résultats, état de chargement/erreur et consultation éventuelle de la requête SPARQL. |
| 5. Intégration et livraison | Élève 5 | Contrats entre les modules, configuration de développement, Docker Compose, documentation, scénarios de validation et assemblage de la démonstration. |

Chaque élève travaille dans son dossier/module et publie son contrat (routes,
format des données ou vocabulaire de l’ontologie) avant l’intégration. Le module 5
coordonne les interfaces ; il ne remplace pas le travail fonctionnel des quatre
autres modules.

## Arborescence initiale

```text
EnergyHomeOnto/
├── energyhomeonto.owx       # Ontologie existante OWL/XML
├── backend/                 # API Spring Boot et moteur local français → SPARQL
├── frontend/                # Application React + TypeScript + Vite
├── data/                    # Jeux de données RDF de démonstration
├── docs/                    # Architecture et contrats d’API
├── docker-compose.yml       # Apache Jena Fuseki
└── README.md
```

## Démarrage prévu

Prérequis : Java 21, Maven, Node.js LTS avec npm, et Docker avec Compose.

1. Démarrer Fuseki : `docker compose up -d fuseki`.
2. Charger l’ontologie et les données d’exemple dans un dataset Fuseki nommé
   `energyhome` (à configurer dans le module d’intégration).
3. Démarrer l’API depuis `backend/` avec `mvn spring-boot:run`.
4. Démarrer l’interface depuis `frontend/` avec `npm install`, puis `npm run dev`.

Le frontend et le backend contiennent un squelette de démarrage. Le chargement
RDF dans Fuseki et l’exécution des requêtes SPARQL restent à implémenter.

## Exemple de recherche intelligente

Phrase saisie : **« Liste les maisons autonomes qui possèdent une batterie »**.

Le moteur local doit reconnaître la classe `MaisonAutonome` et la relation
`possede` vers `Batterie`, puis produire une requête de cette forme (les IRI
doivent être vérifiées par rapport à l’ontologie avant exécution) :

```sparql
PREFIX : <http://www.example.org/energyhomeonto#>
SELECT DISTINCT ?maison WHERE {
  ?maison a :MaisonAutonome ;
          :possede ?equipement .
  ?equipement a :Batterie .
}
```

Le travail IA consiste à coder ce pipeline (normalisation, synonymes, extraction
des concepts et génération contrôlée de SPARQL), puis à enrichir progressivement
les règles et exemples. Il ne s’agit pas de connecter un chatbot/API externe.

## État et prochaines étapes

- [x] Initialiser la structure documentaire du projet et répartir le travail en
  cinq modules.
- [x] Identifier l’ontologie OWL déjà présente et retenir une pile cohérente.
- [ ] Créer les projets React et Spring Boot, puis convenir des contrats d’API.
- [ ] Vérifier et charger l’ontologie dans Fuseki ; ajouter un petit dataset RDF.
- [ ] Implémenter les requêtes directes et la traduction locale français → SPARQL.
- [ ] Relier l’interface à l’API et préparer une démonstration de bout en bout.

## Remarque sur le domaine

L’ontologie actuelle contient des concepts d’énergie résidentielle (par exemple
`Maison`, `MaisonAutonome`, `Batterie`, `PanneauSolaire`, `Eolienne` et
`BatimentPublic`). Elle ne contient pas de classe `Vehicule` dans l’extrait
inspecté. Pour prendre en charge « la liste des véhicules », il faudra étendre
l’ontologie et ajouter les données correspondantes ; l’exemple ci-dessus utilise
donc le domaine déjà présent.
