# Module commun — Recherche intelligente

La recherche intelligente est transverse aux cinq features, ne constitue pas une
feature individuelle et n’est pas attribuée à un seul élève. Les cinq membres
contribuent au frontend, au backend et à la génération/exécution SPARQL.

- Traduction question française → SPARQL avec **spaCy** (`fr_core_news_sm`) :
  tokenisation, lemmatisation, étiquetage morpho-syntaxique, analyse en
  dépendances, puis reconnaissance des termes de l’ontologie, de la négation,
  des comparaisons et des superlatifs.
- Le lexique est construit automatiquement depuis l’ontologie ; les domaines et
  portées des propriétés et le verbe de la phrase choisissent la relation.
- Exécution : rdflib sur le graphe enrichi par le raisonneur OWL RL (owlrl).
- Aucune API de LLM n’est appelée.
- Frontend : `frontend/src/shared/recherche-intelligente/` (affiche résultats,
  analyse spaCy et requête SPARQL générée).
- Backend : `backend/app/shared/recherche/` (`analyse.py`, `vocabulaire.py`,
  `interpreter.py`).
- Toute modification du comportement de recherche s’accompagne d’un cas dans
  `backend/tests/test_api.py`.
- Toute modification passe par une PR vers `main`, relue et coordonnée entre les
  cinq membres.

Le détail de la chaîne de traitement, des exemples et la manière d’ajouter des
synonymes ou des verbes sont dans le `README.md` à la racine (§ 5).
