import re

from fastapi import HTTPException

from app.features.batiments import queries
from app.features.batiments.schemas import (
    Building,
    BuildingDetail,
    BuildingInput,
    EnergyDistribution,
    EquipmentItem,
    Indicators,
    Mutation,
    Option,
    Options,
    OwnerItem,
    SourceItem,
    ZoneItem,
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


def _bool(row: dict[str, str], key: str) -> bool | None:
    if key not in row:
        return None
    val = row[key].lower()
    return val in ("true", "1")


def _building(row: dict[str, str]) -> Building:
    return Building(
        id=local_name(row["building"]),
        name=row["name"],
        kind=row["kinds"],
        consumption=_float(row, "consumption"),
        surface=_float(row, "surface"),
        occupants=_integer(row, "occupants"),
        floors=_integer(row, "floors"),
        energy_class=row.get("energyClass"),
        grid_connected=_bool(row, "gridConnected"),
        latitude=_float(row, "latitude"),
        longitude=_float(row, "longitude"),
        owner_id=row.get("owner"),
        owner_name=row.get("ownerName"),
        zone_id=row.get("zone"),
        zone_name=row.get("zoneName"),
        source_count=int(row.get("sourceCount", 0)),
        equipment_count=int(row.get("equipmentCount", 0)),
    )


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def list_buildings(
    kind: str | None = None,
    text: str | None = None,
    energy_class: str | None = None,
    grid_connected: bool | None = None,
    min_consumption: float | None = None,
    max_consumption: float | None = None,
) -> list[Building]:
    return [
        _building(row)
        for row in query(
            queries.building_list(
                kind=kind,
                text=_clean(text),
                energy_class=energy_class,
                grid_connected=grid_connected,
                min_consumption=min_consumption,
                max_consumption=max_consumption,
            )
        )
    ]


def _is_building(identifier: str) -> bool:
    return ask(queries.is_a(identifier, "Batiment"))


def get_building(identifier: str) -> BuildingDetail:
    identifier = _safe_identifier(identifier)
    if not _is_building(identifier):
        raise HTTPException(status_code=404, detail="Bâtiment introuvable.")
    detail_rows = query(queries.building_detail(identifier))
    if not detail_rows:
        raise HTTPException(status_code=404, detail="Bâtiment introuvable.")

    base_building = _building({**detail_rows[0], "building": f"#{identifier}"})
    all_inferred = [
        local_name(r["class"])
        for r in query(queries.inferred_classes(identifier))
        if local_name(r["class"]) not in ("NamedIndividual", "Thing")
    ]
    specific_kinds = set(base_building.kind.split(", "))
    inferred_classes = [c for c in all_inferred if c not in specific_kinds]

    # Zones (Quartier + Ville inférée par transitivité de :estSitueDans)
    zones = [
        ZoneItem(id=local_name(r["zone"]), name=r["name"], kind=r["kind"])
        for r in query(queries.building_zones(identifier))
    ]

    # Propriétaire (inféré via owl:inverseOf :estProprietaireDe déduit de :appartientA)
    owner_rows = query(queries.building_owner_inferred(identifier))
    owner = None
    if owner_rows:
        r = owner_rows[0]
        owner = OwnerItem(
            id=local_name(r["owner"]),
            name=r["name"],
            kind=r["kind"],
            email=r.get("email"),
            phone=r.get("phone"),
        )

    # Sources d'énergie & stockages
    sources = [
        SourceItem(
            id=local_name(r["source"]),
            name=r["name"],
            kind=r["kinds"],
            power_kw=_float(r, "power"),
            owned=r.get("owned") == "true",
        )
        for r in query(queries.building_energy_sources(identifier))
    ]

    # Équipements installés (compteur intelligent...)
    equipment = [
        EquipmentItem(
            id=local_name(r["equipment"]),
            name=r["name"],
            kind=r["kinds"],
            identifier_number=r.get("identifierNumber"),
        )
        for r in query(queries.building_equipment(identifier))
    ]

    # Lignes électriques reliées
    lines = [
        ZoneItem(id=local_name(r["line"]), name=r["name"], kind=r["kinds"])
        for r in query(queries.building_lines(identifier))
    ]

    is_autonomous = "MaisonAutonome" in all_inferred
    is_smart = "MaisonIntelligente" in all_inferred

    return BuildingDetail(
        **base_building.model_dump(),
        inferred_classes=inferred_classes,
        zones=zones,
        owner=owner,
        sources=sources,
        equipment=equipment,
        lines=lines,
        is_autonomous=is_autonomous,
        is_smart=is_smart,
    )


def get_indicators() -> Indicators:
    rows = query(queries.indicators())
    total_count = int(rows[0]["totalCount"]) if rows and "totalCount" in rows[0] else 0
    avg_conso = _float(rows[0], "avgConsumption") if rows else None
    total_surf = _float(rows[0], "totalSurface") if rows else None
    avg_occ = _float(rows[0], "avgOccupants") if rows else None

    dist_rows = query(queries.energy_class_distribution())
    dist = [
        EnergyDistribution(energy_class=r["energyClass"], count=int(r["count"]))
        for r in dist_rows
    ]

    return Indicators(
        total_count=total_count,
        avg_consumption=avg_conso,
        total_surface=total_surf,
        avg_occupants=avg_occ,
        energy_distribution=dist,
    )


def _options(kind: str) -> list[Option]:
    return [
        Option(id=local_name(row["element"]), name=row["name"], kind=row["kinds"])
        for row in query(queries.options(kind))
    ]


def get_options() -> Options:
    return Options(
        owners=_options("Personne"),
        zones=_options("Zone"),
        sources=_options("SourceEnergie"),
    )


def _checked_option(identifier: str | None, kind: str, label: str) -> str | None:
    if not identifier:
        return None
    if not is_identifier(identifier) or not ask(queries.is_a(identifier, kind)):
        raise HTTPException(status_code=422, detail=f"{label} inconnu(e) : {identifier}.")
    return identifier


def _checked_list(identifiers: list[str], kind: str, label: str) -> list[str]:
    unique = list(dict.fromkeys(identifiers))
    for identifier in unique:
        if not is_identifier(identifier) or not ask(queries.is_a(identifier, kind)):
            raise HTTPException(status_code=422, detail=f"{label} inconnu(e) : {identifier}.")
    return unique


def _data(data: BuildingInput) -> dict:
    return {
        **data.model_dump(),
        "name": data.name.strip(),
        "owner": _checked_option(data.owner, "Personne", "Propriétaire"),
        "zone": _checked_option(data.zone, "Zone", "Zone géographique"),
        "sources": _checked_list(data.sources, "SourceEnergie", "Source d’énergie"),
    }


def _new_identifier(name: str, kind: str) -> str:
    words = re.findall(r"[a-z0-9]+", normalize(name)) or [kind.lower()]
    base = kind.lower() + "".join(word.capitalize() for word in words)
    identifier, suffix = base, 2
    while ask(queries.exists(identifier)):
        identifier, suffix = f"{base}{suffix}", suffix + 1
    return identifier


def create_building(data: BuildingInput) -> Mutation:
    values = _data(data)
    identifier = _new_identifier(values["name"], data.kind)
    sparql = queries.create_building(identifier, data.kind, values)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def _existing(identifier: str) -> str:
    identifier = _safe_identifier(identifier)
    if not _is_building(identifier):
        raise HTTPException(status_code=404, detail="Bâtiment introuvable.")
    return identifier


def update_building(identifier: str, data: BuildingInput) -> Mutation:
    identifier = _existing(identifier)
    sparql = queries.update_building(identifier, data.kind, _data(data))
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def delete_building(identifier: str) -> Mutation:
    identifier = _existing(identifier)
    sparql = queries.delete_building(identifier)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)
