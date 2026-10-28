from typing import Literal

from fastapi import APIRouter, Query

from app.features.territoires_acteurs.schemas import (
    Actor, ActorDetail, ActorInput, Mutation, Territory, TerritoryDetail,
)
from app.features.territoires_acteurs import service

router = APIRouter(prefix="/territoires-acteurs", tags=["Territoires et acteurs"])


@router.get("/territoires", response_model=list[Territory])
def territories(
    kind: Literal["Ville", "Quartier"] | None = None, q: str | None = Query(default=None, max_length=100),
) -> list[Territory]:
    return service.list_territories(kind, q)


@router.get("/territoires/{identifier}", response_model=TerritoryDetail)
def territory(identifier: str) -> TerritoryDetail:
    return service.get_territory(identifier)


@router.get("/acteurs", response_model=list[Actor])
def actors(
    kind: Literal["Personne", "GestionnaireReseau"] | None = None, q: str | None = Query(default=None, max_length=100),
) -> list[Actor]:
    return service.list_actors(kind, q)


@router.get("/acteurs/{identifier}", response_model=ActorDetail)
def actor(identifier: str) -> ActorDetail:
    return service.get_actor(identifier)


@router.post("/acteurs", response_model=Mutation, status_code=201)
def create_actor(data: ActorInput) -> Mutation:
    return service.create_actor(data)


@router.put("/acteurs/{identifier}", response_model=Mutation)
def update_actor(identifier: str, data: ActorInput) -> Mutation:
    return service.update_actor(identifier, data)


@router.delete("/acteurs/{identifier}", response_model=Mutation)
def delete_actor(identifier: str) -> Mutation:
    return service.delete_actor(identifier)
