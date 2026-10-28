import re

from fastapi import HTTPException

from app.features.territoires_acteurs import queries
from app.features.territoires_acteurs.schemas import (
    Actor, ActorDetail, ActorInput, Infrastructure, Mutation, Territory, TerritoryDetail,
)
from app.shared.rdf_store import ask, query, update
from app.shared.recherche.vocabulaire import normalize
from app.shared.sparql import is_identifier, local_name


def _safe_identifier(identifier: str) -> str:
    if not is_identifier(identifier):
        raise HTTPException(status_code=404, detail="Identifiant inconnu.")
    return identifier


def _infrastructure(row: dict[str, str]) -> Infrastructure:
    return Infrastructure(id=local_name(row["element"]), name=row["name"], kind=row["kinds"])


def _territory(row: dict[str, str]) -> Territory:
    return Territory(
        id=local_name(row["territory"]), name=row["name"], kind=row["kind"],
        population=int(row["population"]) if "population" in row else None,
        postal_code=row.get("postalCode"), area_km2=float(row["area"]) if "area" in row else None,
    )


def _actor(row: dict[str, str], identifier: str | None = None) -> Actor:
    return Actor(
        id=identifier or local_name(row["actor"]), name=row["name"], kind=row["kind"],
        email=row.get("email"), phone=row.get("phone"), managed_count=int(row.get("managedCount", 0)),
    )


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def list_territories(kind: str | None = None, text: str | None = None) -> list[Territory]:
    return [_territory(row) for row in query(queries.territory_list(kind, _clean(text)))]


def get_territory(identifier: str) -> TerritoryDetail:
    identifier = _safe_identifier(identifier)
    rows = query(queries.territory_detail(identifier))
    if not rows:
        raise HTTPException(status_code=404, detail="Territoire introuvable.")
    territory = _territory({**rows[0], "territory": f"#{identifier}"})
    infrastructure = [_infrastructure(row) for row in query(queries.territory_infrastructure(identifier))]
    return TerritoryDetail(**territory.model_dump(), infrastructure=infrastructure)


def list_actors(kind: str | None = None, text: str | None = None) -> list[Actor]:
    return [_actor(row) for row in query(queries.actor_list(kind, _clean(text)))]


def get_actor(identifier: str) -> ActorDetail:
    identifier = _safe_identifier(identifier)
    rows = query(queries.actor_detail(identifier))
    if not rows:
        raise HTTPException(status_code=404, detail="Acteur introuvable.")
    actor = _actor(rows[0], identifier)
    equipment = [_infrastructure(row) for row in query(queries.managed_equipment(identifier))]
    buildings = [_infrastructure(row) for row in query(queries.owned_buildings(identifier))]
    return ActorDetail(**actor.model_dump(), managed_equipment=equipment, owned_buildings=buildings)


def _exists(identifier: str) -> bool:
    return ask(queries.actor_exists(identifier))


def _new_identifier(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", normalize(name)) or ["acteur"]
    base = "acteur" + "".join(word.capitalize() for word in words)
    identifier, suffix = base, 2
    while _exists(identifier):
        identifier, suffix = f"{base}{suffix}", suffix + 1
    return identifier


def create_actor(data: ActorInput) -> Mutation:
    identifier = _new_identifier(data.name)
    sparql = queries.create_actor(identifier, data.kind, data.name.strip(), _clean(data.email), _clean(data.phone))
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def update_actor(identifier: str, data: ActorInput) -> Mutation:
    identifier = _safe_identifier(identifier)
    if not query(queries.actor_detail(identifier)):
        raise HTTPException(status_code=404, detail="Acteur introuvable.")
    sparql = queries.update_actor(identifier, data.kind, data.name.strip(), _clean(data.email), _clean(data.phone))
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def delete_actor(identifier: str) -> Mutation:
    identifier = _safe_identifier(identifier)
    if not query(queries.actor_detail(identifier)):
        raise HTTPException(status_code=404, detail="Acteur introuvable.")
    sparql = queries.delete_actor(identifier)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)
