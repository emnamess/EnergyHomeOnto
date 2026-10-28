"""Graphe RDF de l'application : ontologie OWL, modifications CRUD et inférences.

- L'ontologie `energyhomeonto.owx` (Protégé) est lue directement avec owlready2.
- Les requêtes SPARQL Update (CRUD) sont appliquées au graphe puis ajoutées au
  journal `data/journal-crud.rq`, rejoué à chaque démarrage : modifier
  l'ontologie dans Protégé ne fait donc pas perdre les données saisies dans l'application.
- Le raisonneur OWL RL (owlrl) calcule les inférences (classes définies,
  propriétés inverses et transitives, sous-classes...). Les requêtes de lecture
  portent sur le graphe inféré.
"""

import io
import os
import threading
from functools import lru_cache
from pathlib import Path

import owlready2
import owlrl
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_PATH = ROOT / "energyhomeonto.owx"
DEFAULT_JOURNAL_PATH = ROOT / "data" / "journal-crud.rq"
JOURNAL_SEPARATOR = "\n;\n"
OWLRL_ERROR = URIRef("http://www.daml.org/2002/03/agents/agent-ont#ErrorMessage")


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


def _infer(asserted: Graph) -> Graph:
    inferred = Graph()
    for triple in asserted:
        inferred.add(triple)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(inferred)
    for error in list(inferred.subjects(RDF.type, OWLRL_ERROR)):
        inferred.remove((error, None, None))
        inferred.remove((None, None, error))
    return inferred


class RdfStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.version = 0
        self.asserted = _load_ontology()
        path = journal_path()
        if path.exists():
            for statement in path.read_text(encoding="utf-8").split(JOURNAL_SEPARATOR):
                if statement.strip():
                    self.asserted.update(statement)
        self.inferred = _infer(self.asserted)

    def query(self, sparql: str, inferred: bool = True) -> list[dict[str, str]]:
        graph = self.inferred if inferred else self.asserted
        return [
            {str(variable): str(value) for variable, value in row.asdict().items() if value is not None}
            for row in graph.query(sparql)
        ]

    def ask(self, sparql: str) -> bool:
        return bool(self.inferred.query(sparql).askAnswer)

    def update(self, sparql: str) -> None:
        with self._lock:
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
