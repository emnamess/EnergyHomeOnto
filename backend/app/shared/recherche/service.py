from app.shared.recherche.interpreter import InterpretedQuery, interpret
from app.shared.rdf_store import query


def search(question: str) -> tuple[InterpretedQuery, list[dict[str, str]]]:
    interpreted = interpret(question)
    return interpreted, query(interpreted.sparql)
