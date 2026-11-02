from fastapi import APIRouter, Query

from app.features.production import service
from app.features.production.schemas import Indicators, Mutation, Options, Source, SourceDetail, SourceInput, SourceKind

router = APIRouter(prefix="/production", tags=["Production"])


@router.get("/sources", response_model=list[Source])
def sources(
    kind: SourceKind | None = None,
    q: str | None = Query(default=None, max_length=100),
    min_power: float | None = Query(default=None, ge=0),
    renewable: bool | None = None,
) -> list[Source]:
    return service.list_sources(kind, q, min_power, renewable)


@router.get("/indicateurs", response_model=Indicators)
def indicators() -> Indicators:
    return service.get_indicators()


@router.get("/options", response_model=Options)
def options() -> Options:
    return service.get_options()


@router.get("/sources/{identifier}", response_model=SourceDetail)
def source(identifier: str) -> SourceDetail:
    return service.get_source(identifier)


@router.post("/sources", response_model=Mutation, status_code=201)
def create_source(data: SourceInput) -> Mutation:
    return service.create_source(data)


@router.put("/sources/{identifier}", response_model=Mutation)
def update_source(identifier: str, data: SourceInput) -> Mutation:
    return service.update_source(identifier, data)


@router.delete("/sources/{identifier}", response_model=Mutation)
def delete_source(identifier: str) -> Mutation:
    return service.delete_source(identifier)
