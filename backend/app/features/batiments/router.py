from typing import Literal

from fastapi import APIRouter, Query

from app.features.batiments import service
from app.features.batiments.schemas import (
    Building,
    BuildingDetail,
    BuildingInput,
    EnergyClass,
    Indicators,
    Mutation,
    Options,
)

BuildingFilterKind = Literal[
    "Batiment",
    "Maison",
    "BatimentPublic",
    "Ecole",
    "Hopital",
    "Mairie",
    "BatimentIndustriel",
    "BatimentCommercial",
    "MaisonAutonome",
    "MaisonIntelligente",
    "BatimentAlimenteRenouvelable",
    "BatimentAvecStockage",
    "BatimentEconome",
    "GrosConsommateur",
]

router = APIRouter(prefix="/batiments", tags=["Bâtiments"])


@router.get("", response_model=list[Building])
def buildings(
    kind: BuildingFilterKind | None = None,
    q: str | None = Query(default=None, max_length=100),
    energy_class: EnergyClass | None = None,
    grid_connected: bool | None = None,
    min_consumption: float | None = Query(default=None, ge=0),
    max_consumption: float | None = Query(default=None, ge=0),
) -> list[Building]:
    return service.list_buildings(
        kind=kind,
        text=q,
        energy_class=energy_class,
        grid_connected=grid_connected,
        min_consumption=min_consumption,
        max_consumption=max_consumption,
    )


@router.get("/indicateurs", response_model=Indicators)
def indicators() -> Indicators:
    return service.get_indicators()


@router.get("/options", response_model=Options)
def options() -> Options:
    return service.get_options()


@router.get("/{identifier}", response_model=BuildingDetail)
def building(identifier: str) -> BuildingDetail:
    return service.get_building(identifier)


@router.post("", response_model=Mutation, status_code=201)
def create_building(data: BuildingInput) -> Mutation:
    return service.create_building(data)


@router.put("/{identifier}", response_model=Mutation)
def update_building(identifier: str, data: BuildingInput) -> Mutation:
    return service.update_building(identifier, data)


@router.delete("/{identifier}", response_model=Mutation)
def delete_building(identifier: str) -> Mutation:
    return service.delete_building(identifier)
