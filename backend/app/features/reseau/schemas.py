from typing import Literal

from pydantic import BaseModel, Field


NetworkKind = Literal[
    "LigneElectrique", "LigneHauteTension", "LigneMoyenneTension", "LigneBasseTension", "LigneSouterraine",
    "PosteTransformation", "CompteurIntelligent",
]


class RelatedElement(BaseModel):
    id: str
    name: str
    kind: str


class NetworkElement(BaseModel):
    id: str
    name: str
    kind: str
    length: float | None = None
    voltage: float | None = None
    section: float | None = None
    loss_rate: float | None = None
    underground: bool | None = None
    transformation_power: float | None = None
    meter_identifier: str | None = None
    reading_frequency: int | None = None
    installation_year: int | None = None
    lifetime_years: int | None = None
    installation_cost: float | None = None
    related_count: int = 0


class NetworkDetail(NetworkElement):
    inferred_classes: list[str]
    relationships: list[RelatedElement]
    managers: list[RelatedElement]


class KindIndicator(BaseModel):
    kind: str
    count: int


class Indicators(BaseModel):
    count: int
    by_kind: list[KindIndicator]


class Option(BaseModel):
    id: str
    name: str
    kind: str


class Options(BaseModel):
    kinds: list[str]
    lines: list[Option]
    equipment: list[Option]
    managers: list[Option]
    buildings: list[Option]
    sources: list[Option]
    storages: list[Option]


class NetworkInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: NetworkKind
    length: float | None = Field(default=None, gt=0, le=10_000_000)
    voltage: float | None = Field(default=None, gt=0, le=1_000_000)
    section: float | None = Field(default=None, gt=0, le=1_000_000)
    loss_rate: float | None = Field(default=None, ge=0, le=100)
    underground: bool | None = None
    transformation_power: float | None = Field(default=None, gt=0, le=1_000_000)
    meter_identifier: str | None = Field(default=None, max_length=100)
    reading_frequency: int | None = Field(default=None, gt=0, le=3650)
    installation_year: int | None = Field(default=None, ge=1900, le=2100)
    lifetime_years: int | None = Field(default=None, gt=0, le=200)
    installation_cost: float | None = Field(default=None, ge=0, le=1_000_000_000)
    related: list[str] = Field(default_factory=list, max_length=100)
    managers: list[str] = Field(default_factory=list, max_length=50)


class Mutation(BaseModel):
    id: str
    sparql: str
