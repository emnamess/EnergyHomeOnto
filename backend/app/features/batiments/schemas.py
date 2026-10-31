from typing import Literal

from pydantic import BaseModel, Field

BuildingKind = Literal[
    "Maison",
    "BatimentPublic",
    "Ecole",
    "Hopital",
    "Mairie",
    "BatimentIndustriel",
    "BatimentCommercial",
]

EnergyClass = Literal["A", "B", "C", "D", "E", "F", "G"]


class Building(BaseModel):
    id: str
    name: str
    kind: str
    consumption: float | None = None
    surface: float | None = None
    occupants: int | None = None
    floors: int | None = None
    energy_class: str | None = None
    grid_connected: bool | None = None
    latitude: float | None = None
    longitude: float | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    source_count: int = 0
    equipment_count: int = 0


class ZoneItem(BaseModel):
    id: str
    name: str
    kind: str


class OwnerItem(BaseModel):
    id: str
    name: str
    kind: str
    email: str | None = None
    phone: str | None = None


class SourceItem(BaseModel):
    id: str
    name: str
    kind: str
    power_kw: float | None = None
    owned: bool = False


class EquipmentItem(BaseModel):
    id: str
    name: str
    kind: str
    identifier_number: str | None = None


class BuildingDetail(Building):
    inferred_classes: list[str]
    zones: list[ZoneItem]
    owner: OwnerItem | None = None
    sources: list[SourceItem]
    equipment: list[EquipmentItem]
    lines: list[ZoneItem]
    is_autonomous: bool = False
    is_smart: bool = False


class EnergyDistribution(BaseModel):
    energy_class: str
    count: int


class Indicators(BaseModel):
    total_count: int
    avg_consumption: float | None = None
    total_surface: float | None = None
    avg_occupants: float | None = None
    energy_distribution: list[EnergyDistribution]


class Option(BaseModel):
    id: str
    name: str
    kind: str


class Options(BaseModel):
    owners: list[Option]
    zones: list[Option]
    sources: list[Option]


class BuildingInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: BuildingKind = "Maison"
    consumption: float | None = Field(default=None, ge=0, le=1_000_000)
    surface: float | None = Field(default=None, ge=0, le=1_000_000)
    occupants: int | None = Field(default=None, ge=0, le=100_000)
    floors: int | None = Field(default=None, ge=0, le=500)
    energy_class: EnergyClass | None = None
    grid_connected: bool | None = True
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    owner: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    sources: list[str] = Field(default_factory=list, max_length=20)


class Mutation(BaseModel):
    """Résultat d'une écriture : identifiant concerné et requête SPARQL Update exécutée."""
    id: str
    sparql: str
