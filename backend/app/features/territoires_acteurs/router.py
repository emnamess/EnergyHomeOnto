from fastapi import APIRouter

from app.features.territoires_acteurs.schemas import Actor, ActorDetail, Territory, TerritoryDetail
from app.features.territoires_acteurs import service

router = APIRouter(prefix="/territoires-acteurs", tags=["Territoires et acteurs"])


@router.get("/territoires", response_model=list[Territory])
async def territories() -> list[Territory]:
    return await service.list_territories()


@router.get("/territoires/{identifier}", response_model=TerritoryDetail)
async def territory(identifier: str) -> TerritoryDetail:
    return await service.get_territory(identifier)


@router.get("/acteurs", response_model=list[Actor])
async def actors() -> list[Actor]:
    return await service.list_actors()


@router.get("/acteurs/{identifier}", response_model=ActorDetail)
async def actor(identifier: str) -> ActorDetail:
    return await service.get_actor(identifier)
