"""Chargement local du graphe RDF et exécution des requêtes SPARQL."""

from functools import lru_cache
from pathlib import Path

from rdflib import Graph

DATASET_PATH = Path(__file__).resolve().parents[3] / "data" / "energyhomeonto.ttl"


@lru_cache(maxsize=1)
def graph() -> Graph:
    if not DATASET_PATH.exists():
        raise RuntimeError(f"Fichier RDF introuvable : {DATASET_PATH}")
    rdf_graph = Graph()
    rdf_graph.parse(DATASET_PATH, format="turtle")
    return rdf_graph


def query(sparql: str) -> list[dict[str, str]]:
    result = graph().query(sparql)
    return [
        {str(variable): str(value) for variable, value in row.asdict().items() if value is not None}
        for row in result
    ]
