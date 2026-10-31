"""Graphe RDF de l'application : ontologie OWL, modifications CRUD et inférences.

- L'ontologie `energyhomeonto.owx` (Protégé) est lue directement avec owlready2.
- Les requêtes SPARQL Update (CRUD) sont appliquées au graphe puis ajoutées au
  journal `data/journal-crud.rq`, rejoué à chaque démarrage : modifier
  l'ontologie dans Protégé ne fait donc pas perdre les données saisies dans l'application.
- Le raisonneur OWL RL (owlrl) calcule les inférences (classes définies,
  propriétés inverses et transitives, sous-classes...), complétées par les
  classes définies par un seuil numérique. Les requêtes de lecture portent sur
  le graphe inféré.
"""

import io
import os
import threading
from functools import lru_cache
from pathlib import Path

import owlready2
import owlrl
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_PATH = ROOT / "energyhomeonto.owx"
DEFAULT_JOURNAL_PATH = ROOT / "data" / "journal-crud.rq"
JOURNAL_SEPARATOR = "\n;\n"
OWLRL_ERROR = URIRef("http://www.daml.org/2002/03/agents/agent-ont#ErrorMessage")
# Le parseur SPARQL de rdflib (pyparsing) n'est pas thread-safe : deux requêtes
# analysées en même temps le corrompent durablement. FastAPI exécutant les routes
# dans plusieurs threads, tout accès SPARQL passe par ce verrou global.
SPARQL_LOCK = threading.RLock()

FACETS = {"minInclusive": ">=", "minExclusive": ">", "maxInclusive": "<=", "maxExclusive": "<"}
DATATYPE_DEFINITIONS = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?class ?base ?property ?facet ?limit WHERE {
  ?class owl:equivalentClass/owl:intersectionOf ?list . FILTER(isIRI(?class))
  ?list rdf:rest*/rdf:first ?base . FILTER(isIRI(?base))
  ?list rdf:rest*/rdf:first ?restriction .
  ?restriction owl:onProperty ?property ; owl:someValuesFrom ?datatype .
  ?datatype owl:withRestrictions/rdf:rest*/rdf:first ?bound .
  ?bound ?facet ?limit .
  FILTER(?facet IN (xsd:minInclusive, xsd:minExclusive, xsd:maxInclusive, xsd:maxExclusive))
}"""


def journal_path() -> Path:
    return Path(os.environ.get("ENERGYHOME_JOURNAL", DEFAULT_JOURNAL_PATH))


def _load_ontology() -> Graph:
    if not ONTOLOGY_PATH.exists():
        raise RuntimeError(f"Ontologie introuvable : {ONTOLOGY_PATH}")
    world = owlready2.World()
    with ONTOLOGY_PATH.open("rb") as source:
        ontology = world.get_ontology("http://www.example.org/energyhomeonto").load(fileobj=source)
    buffer = io.BytesIO()
    ontology.save(file=buffer, format="ntriples")
    graph = Graph()
    graph.parse(data=buffer.getvalue().decode("utf-8"), format="nt")
    return graph


def _apply_datatype_restrictions(graph: Graph) -> None:
    """Classes définies par un seuil numérique (ex. GrosConsommateur ≡ Batiment ⊓ ∃consommation.[≥ 50]).

    Le profil OWL RL d'owlrl n'évalue pas les facettes de types de données
    (xsd:minInclusive...). Cette étape lit ces définitions dans l'ontologie et
    classe les individus qui respectent le seuil, ainsi que dans les superclasses.
    """
    definitions: dict[tuple, list[str]] = {}
    for row in graph.query(DATATYPE_DEFINITIONS):
        operator = FACETS[str(row.facet).rsplit("#", 1)[-1]]
        definitions.setdefault((row["class"], row.base, row.property), []).append(f"?v {operator} {row.limit.n3()}")
    for (defined_class, base, prop), conditions in definitions.items():
        members = graph.query(f"SELECT DISTINCT ?x WHERE {{ ?x a <{base}> ; <{prop}> ?v . FILTER({' && '.join(conditions)}) }}")
        classes = {defined_class, *(c for c in graph.objects(defined_class, RDFS.subClassOf) if isinstance(c, URIRef))}
        for (member,) in members:
            for cls in classes:
                graph.add((member, RDF.type, cls))


def _infer(asserted: Graph) -> Graph:
    inferred = Graph()
    for triple in asserted:
        inferred.add(triple)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(inferred)
    for error in list(inferred.subjects(RDF.type, OWLRL_ERROR)):
        inferred.remove((error, None, None))
        inferred.remove((None, None, error))
    _apply_datatype_restrictions(inferred)
    return inferred


class RdfStore:
    def __init__(self) -> None:
        self.version = 0
        self.asserted = _load_ontology()
        path = journal_path()
        with SPARQL_LOCK:
            if path.exists():
                for statement in path.read_text(encoding="utf-8").split(JOURNAL_SEPARATOR):
                    if statement.strip():
                        self.asserted.update(statement)
            self.inferred = _infer(self.asserted)

    def query(self, sparql: str, inferred: bool = True) -> list[dict[str, str]]:
        graph = self.inferred if inferred else self.asserted
        with SPARQL_LOCK:
            return [
                {str(variable): str(value) for variable, value in row.asdict().items() if value is not None}
                for row in graph.query(sparql)
            ]

    def ask(self, sparql: str) -> bool:
        with SPARQL_LOCK:
            return bool(self.inferred.query(sparql).askAnswer)

    def update(self, sparql: str) -> None:
        with SPARQL_LOCK:
            self.asserted.update(sparql)
            path = journal_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as journal:
                journal.write(sparql.strip() + JOURNAL_SEPARATOR)
            self.inferred = _infer(self.asserted)
            self.version += 1


@lru_cache(maxsize=1)
def store() -> RdfStore:
    return RdfStore()


def query(sparql: str, inferred: bool = True) -> list[dict[str, str]]:
    return store().query(sparql, inferred)


def ask(sparql: str) -> bool:
    return store().ask(sparql)


def update(sparql: str) -> None:
    store().update(sparql)
