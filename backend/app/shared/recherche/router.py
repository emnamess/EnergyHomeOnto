from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.shared.recherche.service import search

router = APIRouter(tags=["Recherche intelligente"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class SearchResponse(BaseModel):
    interpretation: str
    sparql: str
    results: list[dict[str, str]]


@router.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest) -> SearchResponse:
    try:
        query, results = await search(request.query)
        return SearchResponse(interpretation=query.interpretation, sparql=query.sparql, results=results)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Impossible d'interroger le graphe RDF local. Vérifiez le fichier data/energyhomeonto.ttl.",
        ) from error
