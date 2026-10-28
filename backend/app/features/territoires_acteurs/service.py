import re

from fastapi import HTTPException

from app.features.territoires_acteurs import queries
from app.features.territoires_acteurs.schemas import Actor, ActorDetail, Infrastructure, Territory, TerritoryDetail
from app.shared.recherche.service import execute_sparql


def _identifier(uri: str) -> str:
    return uri.rsplit("#", 1)[-1]


def _safe_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", identifier):
        raise HTTPException(status_code=404, detail="Identifiant inconnu.")
    return identifier


def _infrastructure(row: dict[str, str]) -> Infrastructure:
    return Infrastructure(id=_identifier(row["element"]), name=row["name"], kind=row["kind"])


def _territory(row: dict[str, str]) -> Territory:
    return Territory(
        id=_identifier(row["territory"]), name=row["name"], kind=row["kind"],
        population=int(row["population"]) if "population" in row else None,
        postal_code=row.get("postalCode"), area_km2=float(row["area"]) if "area" in row else None,
    )


def _actor(row: dict[str, str], identifier: str | None = None) -> Actor:
    return Actor(
        id=identifier or _identifier(row["actor"]), name=row["name"], kind=row["kind"],
        email=row.get("email"), phone=row.get("phone"), managed_count=int(row.get("managedCount", 0)),
    )


def list_territories() -> list[Territory]:
    return [_territory(row) for row in execute_sparql(queries.territory_list())]


def get_territory(identifier: str) -> TerritoryDetail:
    identifier = _safe_identifier(identifier)
    rows = execute_sparql(queries.territory_detail(identifier))
    if not rows:
        raise HTTPException(status_code=404, detail="Territoire introuvable.")
    territory = _territory({**rows[0], "territory": f"#{identifier}"})
    infrastructure = [_infrastructure(row) for row in execute_sparql(queries.territory_infrastructure(identifier))]
    return TerritoryDetail(**territory.model_dump(), infrastructure=infrastructure)


def list_actors() -> list[Actor]:
    return [_actor(row) for row in execute_sparql(queries.actor_list())]


def get_actor(identifier: str) -> ActorDetail:
    identifier = _safe_identifier(identifier)
    rows = execute_sparql(queries.actor_detail(identifier))
    if not rows:
        raise HTTPException(status_code=404, detail="Acteur introuvable.")
    actor = _actor(rows[0], identifier)
    equipment = [_infrastructure(row) for row in execute_sparql(queries.managed_equipment(identifier))]
    return ActorDetail(**actor.model_dump(), managed_equipment=equipment)
