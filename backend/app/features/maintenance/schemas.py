import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Equipment(BaseModel):
    id: str
    name: str
    category: str
    kind: str
    inferred_classes: list[str] = []
    installation_year: int | None = None
    lifetime_years: int | None = None
    age_years: int | None = None
    remaining_years: int | None = None
    status: Literal["fin-de-vie", "a-remplacer", "en-service", "inconnu"]
    intervention_count: int = 0


class Intervention(BaseModel):
    id: str
    kind: str
    date: datetime.date
    planned: bool
    cost: float | None = None
    description: str
    provider: str | None = None
    equipment_id: str
    equipment_name: str


class EquipmentDetail(Equipment):
    installation_cost: float | None = None
    maintenance_cost: float
    interventions: list[Intervention]


class InterventionInput(BaseModel):
    kind: Literal["InterventionPreventive", "InterventionCorrective"] = "InterventionPreventive"
    equipment: str = Field(min_length=1, max_length=80)
    date: datetime.date
    cost: float | None = Field(default=None, ge=0, le=1_000_000_000)
    description: str = Field(min_length=1, max_length=300)
    provider: str | None = Field(default=None, max_length=120)


class Mutation(BaseModel):
    """Résultat d'une écriture : identifiant concerné et requête SPARQL Update exécutée."""
    id: str
    sparql: str
