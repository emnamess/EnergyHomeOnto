from typing import Literal

from pydantic import BaseModel, Field

StorageKind = Literal["Batterie", "BatterieLithium", "BatteriePlomb", "SuperCondensateur", "StockageHydrogene"]


class Storage(BaseModel):
    id: str
    name: str
    kind: str
    capacity_kwh: float | None = None
    charge_percent: float | None = None
    available_kwh: float | None = None
    recharge_time_h: float | None = None
    charge_cycles: int | None = None
    lifetime_years: int | None = None
    installation_year: int | None = None
    installation_cost: float | None = None
    source_count: int = 0
    building_count: int = 0


class Linked(BaseModel):
    id: str
    name: str
    kind: str
    power_kw: float | None = None
    consumption: float | None = None
    inferred_with_storage: bool = False


class StorageDetail(Storage):
    inferred_classes: list[str]
    sources: list[Linked]
    buildings: list[Linked]


class KindIndicator(BaseModel):
    kind: str
    count: int
    total_capacity_kwh: float
    available_kwh: float
    average_charge_percent: float


class Indicators(BaseModel):
    count: int
    total_capacity_kwh: float
    available_kwh: float
    average_charge_percent: float
    by_kind: list[KindIndicator]


class Option(BaseModel):
    id: str
    name: str
    kind: str


class Options(BaseModel):
    sources: list[Option]
    buildings: list[Option]


class StorageInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: StorageKind = "BatterieLithium"
    capacity: float = Field(gt=0, le=1_000_000)
    # niveauCharge est restreint à [0 ; 100] dans l'ontologie.
    charge: float = Field(ge=0, le=100)
    recharge_time: float | None = Field(default=None, ge=0, le=1000)
    cycles: int | None = Field(default=None, ge=0, le=1_000_000)
    lifetime: int | None = Field(default=None, ge=0, le=200)
    installation_year: int | None = Field(default=None, ge=1900, le=2100)
    installation_cost: float | None = Field(default=None, ge=0, le=1_000_000_000)
    sources: list[str] = Field(default_factory=list, max_length=50)
    buildings: list[str] = Field(default_factory=list, max_length=50)


class Mutation(BaseModel):
    """Résultat d'une écriture : identifiant concerné et requête SPARQL Update exécutée."""
    id: str
    sparql: str
