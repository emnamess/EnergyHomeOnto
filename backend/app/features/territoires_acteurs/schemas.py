from typing import Literal

from pydantic import BaseModel, Field


class Territory(BaseModel):
    id: str
    name: str
    kind: str
    population: int | None = None
    postal_code: str | None = None
    area_km2: float | None = None


class Infrastructure(BaseModel):
    id: str
    name: str
    kind: str


class TerritoryDetail(Territory):
    infrastructure: list[Infrastructure]


class Actor(BaseModel):
    id: str
    name: str
    kind: str
    email: str | None = None
    phone: str | None = None
    managed_count: int = 0


class ActorDetail(Actor):
    managed_equipment: list[Infrastructure]
    owned_buildings: list[Infrastructure]


class ActorInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["Personne", "GestionnaireReseau"] = "Personne"
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)


class Mutation(BaseModel):
    """Résultat d'une écriture : identifiant concerné et requête SPARQL Update exécutée."""
    id: str
    sparql: str
