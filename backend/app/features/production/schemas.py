from typing import Literal

from pydantic import BaseModel, Field

SourceKind = Literal["PanneauSolaire", "Eolienne", "CentraleHydraulique", "CentraleThermique", "GroupeElectrogene"]


class Source(BaseModel):
    id: str
    name: str
    kind: str
    renewable: bool
    power_kw: float | None = None
    efficiency_percent: float | None = None
    annual_production_mwh: float | None = None
    co2_g_per_kwh: float | None = None
    installation_year: int | None = None
    lifetime_years: int | None = None
    installation_cost: float | None = None
    owner: str | None = None
    building_count: int = 0
    storage_count: int = 0


class Linked(BaseModel):
    id: str
    name: str
    kind: str


class SourceDetail(Source):
    panel_surface_m2: float | None = None
    tilt_degrees: float | None = None
    rotor_diameter_m: float | None = None
    mast_height_m: float | None = None
    cut_in_wind_ms: float | None = None
    water_flow_m3s: float | None = None
    fuel_type: str | None = None
    inferred_classes: list[str]
    owners: list[Linked]
    buildings: list[Linked]
    storages: list[Linked]
    zone: Linked | None = None


class KindIndicator(BaseModel):
    kind: str
    renewable: bool
    count: int
    total_power_kw: float
    annual_production_mwh: float


class Indicators(BaseModel):
    count: int
    total_power_kw: float
    annual_production_mwh: float
    renewable_share_percent: float
    average_co2_g_per_kwh: float
    by_kind: list[KindIndicator]


class Options(BaseModel):
    buildings: list[Linked]
    storages: list[Linked]
    zones: list[Linked]


class SourceInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: SourceKind = "PanneauSolaire"
    power: float = Field(gt=0, le=10_000_000)
    # rendement est restreint à [0 ; 100] dans l'ontologie.
    efficiency: float | None = Field(default=None, ge=0, le=100)
    annual_production: float | None = Field(default=None, ge=0, le=100_000_000)
    co2: float | None = Field(default=None, ge=0, le=10_000)
    installation_year: int | None = Field(default=None, ge=1900, le=2100)
    lifetime: int | None = Field(default=None, ge=0, le=200)
    installation_cost: float | None = Field(default=None, ge=0, le=1_000_000_000)
    panel_surface: float | None = Field(default=None, gt=0, le=1_000_000)
    tilt: float | None = Field(default=None, ge=0, le=90)
    rotor_diameter: float | None = Field(default=None, gt=0, le=500)
    mast_height: float | None = Field(default=None, gt=0, le=500)
    cut_in_wind: float | None = Field(default=None, ge=0, le=100)
    water_flow: float | None = Field(default=None, ge=0, le=100_000)
    fuel_type: str | None = Field(default=None, max_length=60)
    owner: str | None = Field(default=None, max_length=80)
    zone: str | None = Field(default=None, max_length=80)
    buildings: list[str] = Field(default_factory=list, max_length=50)
    storages: list[str] = Field(default_factory=list, max_length=50)


class Mutation(BaseModel):
    """Résultat d'une écriture : identifiant concerné et requête SPARQL Update exécutée."""
    id: str
    sparql: str
