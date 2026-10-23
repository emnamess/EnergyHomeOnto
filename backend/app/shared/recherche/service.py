import os

import httpx

from app.shared.recherche.interpreter import InterpretedQuery, interpret

FUSEKI_QUERY_URL = os.getenv("FUSEKI_QUERY_URL", "http://localhost:3030/energyhome/query")


async def execute_sparql(query: str) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            FUSEKI_QUERY_URL,
            content=query,
            headers={"Content-Type": "application/sparql-query", "Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
    bindings = response.json().get("results", {}).get("bindings", [])
    return [{key: value["value"] for key, value in binding.items()} for binding in bindings]


async def search(question: str) -> tuple[InterpretedQuery, list[dict[str, str]]]:
    query = interpret(question)
    return query, await execute_sparql(query.sparql)
