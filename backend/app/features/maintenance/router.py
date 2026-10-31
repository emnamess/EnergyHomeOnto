from typing import Literal

from fastapi import APIRouter, Query

from app.features.maintenance.schemas import Equipment, EquipmentDetail, Intervention, InterventionInput, Mutation
from app.features.maintenance import service

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


@router.get("/equipements", response_model=list[Equipment])
def equipment_list(
    category: Literal["SourceEnergie", "Stockage", "EquipementReseau"] | None = None,
    q: str | None = Query(default=None, max_length=100),
    horizon: int | None = Query(default=None, ge=0, le=100),
) -> list[Equipment]:
    return service.list_equipment(category, q, horizon)


@router.get("/equipements/{identifier}", response_model=EquipmentDetail)
def equipment(identifier: str) -> EquipmentDetail:
    return service.get_equipment(identifier)


@router.get("/interventions", response_model=list[Intervention])
def interventions(
    kind: Literal["InterventionPreventive", "InterventionCorrective"] | None = None,
    q: str | None = Query(default=None, max_length=100),
) -> list[Intervention]:
    return service.list_interventions(kind, q)


@router.get("/interventions/{identifier}", response_model=Intervention)
def intervention(identifier: str) -> Intervention:
    return service.get_intervention(identifier)


@router.post("/interventions", response_model=Mutation, status_code=201)
def create_intervention(data: InterventionInput) -> Mutation:
    return service.create_intervention(data)


@router.put("/interventions/{identifier}", response_model=Mutation)
def update_intervention(identifier: str, data: InterventionInput) -> Mutation:
    return service.update_intervention(identifier, data)


@router.delete("/interventions/{identifier}", response_model=Mutation)
def delete_intervention(identifier: str) -> Mutation:
    return service.delete_intervention(identifier)
