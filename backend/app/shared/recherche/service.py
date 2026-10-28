from app.shared.recherche.interpreter import InterpretedQuery, interpret
from app.shared.rdf_store import query as execute_local_query


async def execute_sparql(query: str) -> list[dict[str, str]]:
    return execute_local_query(query)


async def search(question: str) -> tuple[InterpretedQuery, list[dict[str, str]]]:
    query = interpret(question)
    return query, await execute_sparql(query.sparql)
