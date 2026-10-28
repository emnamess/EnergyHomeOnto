from pydantic import BaseModel


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
