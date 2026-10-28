from fastapi import APIRouter

from app.features.territoires_acteurs.schemas import Actor, ActorDetail, Territory, TerritoryDetail
from app.features.territoires_acteurs import service

router = APIRouter(prefix="/territoires-acteurs", tags=["Territoires et acteurs"])


@router.get("/territoires", response_model=list[Territory])
def territories() -> list[Territory]:
    return service.list_territories()


@router.get("/territoires/{identifier}", response_model=TerritoryDetail)
def territory(identifier: str) -> TerritoryDetail:
    return service.get_territory(identifier)


@router.get("/acteurs", response_model=list[Actor])
def actors() -> list[Actor]:
    return service.list_actors()


@router.get("/acteurs/{identifier}", response_model=ActorDetail)
def actor(identifier: str) -> ActorDetail:
    return service.get_actor(identifier)
