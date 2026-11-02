from fastapi import APIRouter, Query

from app.features.reseau import service
from app.features.reseau.queries import NETWORK_CLASSES
from app.features.reseau.schemas import Indicators, Mutation, NetworkDetail, NetworkElement, NetworkInput, Options

router = APIRouter(prefix="/reseau", tags=["Réseau énergétique"])


@router.get("", response_model=list[NetworkElement])
def elements(
    kind: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    min_voltage: float | None = Query(default=None, ge=0),
    max_voltage: float | None = Query(default=None, ge=0),
    underground: bool | None = None,
) -> list[NetworkElement]:
    if kind is not None and kind not in NETWORK_CLASSES:
        return []
    return service.list_elements(kind, q, min_voltage, max_voltage, underground)


@router.get("/indicateurs", response_model=Indicators)
def indicators() -> Indicators:
    return service.get_indicators()


@router.get("/options", response_model=Options)
def options() -> Options:
    return service.get_options()


@router.get("/{identifier}", response_model=NetworkDetail)
def element(identifier: str) -> NetworkDetail:
    return service.get_element(identifier)


@router.post("", response_model=Mutation, status_code=201)
def create_element(data: NetworkInput) -> Mutation:
    return service.create_element(data)


@router.put("/{identifier}", response_model=Mutation)
def update_element(identifier: str, data: NetworkInput) -> Mutation:
    return service.update_element(identifier, data)


@router.delete("/{identifier}", response_model=Mutation)
def delete_element(identifier: str) -> Mutation:
    return service.delete_element(identifier)
