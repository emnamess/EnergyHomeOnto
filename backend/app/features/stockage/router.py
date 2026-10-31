from typing import Literal

from fastapi import APIRouter, Query

from app.features.stockage import service
from app.features.stockage.schemas import Indicators, Mutation, Options, Storage, StorageDetail, StorageInput, StorageKind

router = APIRouter(prefix="/stockages", tags=["Stockage"])


@router.get("", response_model=list[Storage])
def storages(
    kind: StorageKind | None = None,
    q: str | None = Query(default=None, max_length=100),
    min_capacity: float | None = Query(default=None, ge=0),
    charge: Literal["faible", "moyen", "eleve"] | None = None,
) -> list[Storage]:
    return service.list_storages(kind, q, min_capacity, charge)


@router.get("/indicateurs", response_model=Indicators)
def indicators() -> Indicators:
    return service.get_indicators()


@router.get("/options", response_model=Options)
def options() -> Options:
    return service.get_options()


@router.get("/{identifier}", response_model=StorageDetail)
def storage(identifier: str) -> StorageDetail:
    return service.get_storage(identifier)


@router.post("", response_model=Mutation, status_code=201)
def create_storage(data: StorageInput) -> Mutation:
    return service.create_storage(data)


@router.put("/{identifier}", response_model=Mutation)
def update_storage(identifier: str, data: StorageInput) -> Mutation:
    return service.update_storage(identifier, data)


@router.delete("/{identifier}", response_model=Mutation)
def delete_storage(identifier: str) -> Mutation:
    return service.delete_storage(identifier)
