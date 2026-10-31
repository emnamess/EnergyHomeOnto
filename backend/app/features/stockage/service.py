import re

from fastapi import HTTPException

from app.features.stockage import queries
from app.features.stockage.schemas import (
    Indicators, KindIndicator, Linked, Mutation, Option, Options, Storage, StorageDetail, StorageInput,
)
from app.shared.rdf_store import ask, query, update
from app.shared.recherche.vocabulaire import normalize
from app.shared.sparql import is_identifier, local_name


def _safe_identifier(identifier: str) -> str:
    if not is_identifier(identifier):
        raise HTTPException(status_code=404, detail="Identifiant inconnu.")
    return identifier


def _float(row: dict[str, str], key: str) -> float | None:
    return round(float(row[key]), 2) if key in row else None


def _integer(row: dict[str, str], key: str) -> int | None:
    return int(float(row[key])) if key in row else None


def _storage(row: dict[str, str]) -> Storage:
    return Storage(
        id=local_name(row["storage"]), name=row["name"], kind=row["kinds"],
        capacity_kwh=_float(row, "capacity"), charge_percent=_float(row, "charge"), available_kwh=_float(row, "available"),
        recharge_time_h=_float(row, "rechargeTime"), charge_cycles=_integer(row, "cycles"),
        lifetime_years=_integer(row, "lifetime"), installation_year=_integer(row, "year"),
        installation_cost=_float(row, "installationCost"),
        source_count=int(row.get("sourceCount", 0)), building_count=int(row.get("buildingCount", 0)),
    )


def _linked(row: dict[str, str], inferred: set[str] = frozenset()) -> Linked:
    identifier = local_name(row["element"])
    return Linked(
        id=identifier, name=row["name"], kind=row["kinds"], power_kw=_float(row, "power"),
        consumption=_float(row, "consumption"), inferred_with_storage=identifier in inferred,
    )


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def list_storages(
    kind: str | None = None, text: str | None = None, min_capacity: float | None = None, charge: str | None = None,
) -> list[Storage]:
    return [_storage(row) for row in query(queries.storage_list(kind, _clean(text), min_capacity, charge))]


def _is_storage(identifier: str) -> bool:
    return ask(queries.is_a(identifier, "Stockage"))


def get_storage(identifier: str) -> StorageDetail:
    identifier = _safe_identifier(identifier)
    if not _is_storage(identifier):
        raise HTTPException(status_code=404, detail="Stockage introuvable.")
    storage = _storage({**query(queries.storage_detail(identifier))[0], "storage": f"#{identifier}"})
    specific = set(storage.kind.split(", "))
    inferred = [local_name(row["class"]) for row in query(queries.inferred_classes(identifier))]
    with_storage = {local_name(row["building"]) for row in query(queries.storage_buildings_inferred(identifier))}
    return StorageDetail(
        **storage.model_dump(),
        inferred_classes=[kind for kind in inferred if kind not in specific],
        sources=[_linked(row) for row in query(queries.storage_sources(identifier))],
        buildings=[_linked(row, with_storage) for row in query(queries.storage_buildings(identifier))],
    )


def get_indicators() -> Indicators:
    rows = query(queries.indicators())
    by_kind = [
        KindIndicator(
            kind=row["kind"], count=int(row["count"]), total_capacity_kwh=round(float(row["totalCapacity"]), 2),
            available_kwh=round(float(row["totalAvailable"]), 2), average_charge_percent=round(float(row["averageCharge"]), 1),
        )
        for row in rows
    ]
    # Totaux calculés sur les valeurs exactes, arrondis une seule fois.
    count = sum(int(row["count"]) for row in rows)
    total = sum(float(row["totalCapacity"]) for row in rows)
    available = sum(float(row["totalAvailable"]) for row in rows)
    charges = sum(float(row["averageCharge"]) * int(row["count"]) for row in rows)
    return Indicators(
        count=count, total_capacity_kwh=round(total, 2), available_kwh=round(available, 2),
        average_charge_percent=round(charges / count, 1) if count else 0, by_kind=by_kind,
    )


def _options(kind: str) -> list[Option]:
    return [
        Option(id=local_name(row["element"]), name=row["name"], kind=row["kinds"])
        for row in query(queries.options(kind))
    ]


def get_options() -> Options:
    return Options(sources=_options("SourceEnergie"), buildings=_options("Batiment"))


def _checked(identifiers: list[str], kind: str, label: str) -> list[str]:
    unique = list(dict.fromkeys(identifiers))
    for identifier in unique:
        if not is_identifier(identifier) or not ask(queries.is_a(identifier, kind)):
            raise HTTPException(status_code=422, detail=f"{label} inconnu(e) : {identifier}.")
    return unique


def _data(data: StorageInput) -> dict:
    if data.cycles is not None and data.kind not in queries.BATTERY_CLASSES:
        # nombreCyclesCharge a pour domaine Batterie : l'utiliser sur un supercondensateur ou un
        # stockage hydrogène rendrait l'ontologie incohérente (classes disjointes).
        raise HTTPException(status_code=422, detail="Le nombre de cycles ne concerne que les batteries.")
    return {
        **data.model_dump(), "name": data.name.strip(),
        "sources": _checked(data.sources, "SourceEnergie", "Source d’énergie"),
        "buildings": _checked(data.buildings, "Batiment", "Bâtiment"),
    }


def _new_identifier(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", normalize(name)) or ["stockage"]
    base = "stockage" + "".join(word.capitalize() for word in words)
    identifier, suffix = base, 2
    while ask(queries.exists(identifier)):
        identifier, suffix = f"{base}{suffix}", suffix + 1
    return identifier


def create_storage(data: StorageInput) -> Mutation:
    values = _data(data)
    identifier = _new_identifier(values["name"])
    sparql = queries.create_storage(identifier, data.kind, values)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def _existing(identifier: str) -> str:
    identifier = _safe_identifier(identifier)
    if not _is_storage(identifier):
        raise HTTPException(status_code=404, detail="Stockage introuvable.")
    return identifier


def update_storage(identifier: str, data: StorageInput) -> Mutation:
    identifier = _existing(identifier)
    sparql = queries.update_storage(identifier, data.kind, _data(data))
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def delete_storage(identifier: str) -> Mutation:
    identifier = _existing(identifier)
    if ask(queries.has_interventions(identifier)):
        raise HTTPException(
            status_code=409,
            detail="Ce stockage a un historique de maintenance : supprimez d’abord ses interventions.",
        )
    sparql = queries.delete_storage(identifier)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)
