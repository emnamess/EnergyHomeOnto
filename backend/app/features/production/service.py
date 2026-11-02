import re

from fastapi import HTTPException

from app.features.production import queries
from app.features.production.schemas import (
    Indicators, KindIndicator, Linked, Mutation, Options, Source, SourceDetail, SourceInput,
)
from app.shared.rdf_store import ask, query, update
from app.shared.recherche.vocabulaire import normalize
from app.shared.sparql import is_identifier, local_name

# Champ du formulaire -> propriété de données de l'ontologie.
FIELDS = {
    "power": "puissance", "efficiency": "rendement", "annual_production": "productionAnnuelle", "co2": "emissionCO2",
    "installation_cost": "coutInstallation", "lifetime": "dureeVie", "installation_year": "anneeInstallation",
    "panel_surface": "surfacePanneau", "tilt": "inclinaison", "rotor_diameter": "diametreRotor",
    "mast_height": "hauteurMat", "cut_in_wind": "vitesseVentDemarrage", "water_flow": "debitEau",
    "fuel_type": "typeCombustible",
}
LABELS = {
    "surfacePanneau": "La surface des panneaux", "inclinaison": "L’inclinaison", "diametreRotor": "Le diamètre du rotor",
    "hauteurMat": "La hauteur du mât", "vitesseVentDemarrage": "La vitesse de démarrage", "debitEau": "Le débit d’eau",
    "typeCombustible": "Le type de combustible",
}


def _safe_identifier(identifier: str) -> str:
    if not is_identifier(identifier):
        raise HTTPException(status_code=404, detail="Identifiant inconnu.")
    return identifier


def _float(row: dict[str, str], key: str) -> float | None:
    return round(float(row[key]), 2) if key in row else None


def _integer(row: dict[str, str], key: str) -> int | None:
    return int(float(row[key])) if key in row else None


def _source(row: dict[str, str]) -> Source:
    return Source(
        id=local_name(row["source"]), name=row["name"], kind=row["kind"], renewable=row["renewable"] == "true",
        power_kw=_float(row, "puissance"), efficiency_percent=_float(row, "rendement"),
        annual_production_mwh=_float(row, "productionAnnuelle"), co2_g_per_kwh=_float(row, "emissionCO2"),
        installation_year=_integer(row, "anneeInstallation"), lifetime_years=_integer(row, "dureeVie"),
        installation_cost=_float(row, "coutInstallation"), owner=row.get("owner"),
        building_count=int(row.get("buildingCount", 0)), storage_count=int(row.get("storageCount", 0)),
    )


def _linked(row: dict[str, str]) -> Linked:
    return Linked(id=local_name(row["element"]), name=row["name"], kind=row["kinds"])


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def list_sources(
    kind: str | None = None, text: str | None = None, min_power: float | None = None, renewable: bool | None = None,
) -> list[Source]:
    return [_source(row) for row in query(queries.source_list(kind, _clean(text), min_power, renewable))]


def _is_source(identifier: str) -> bool:
    return ask(queries.is_a(identifier, "SourceEnergie"))


def get_source(identifier: str) -> SourceDetail:
    identifier = _existing(identifier)
    row = {**query(queries.source_detail(identifier))[0], "source": f"#{identifier}"}
    source = _source(row)
    hidden = {source.kind, "SourceEnergie", "EquipementMaintenable"}
    zone = [_linked(r) for r in query(queries.source_zone(identifier))]
    return SourceDetail(
        **source.model_dump(),
        panel_surface_m2=_float(row, "surfacePanneau"), tilt_degrees=_float(row, "inclinaison"),
        rotor_diameter_m=_float(row, "diametreRotor"), mast_height_m=_float(row, "hauteurMat"),
        cut_in_wind_ms=_float(row, "vitesseVentDemarrage"), water_flow_m3s=_float(row, "debitEau"),
        fuel_type=row.get("typeCombustible"),
        inferred_classes=[c for c in (local_name(r["class"]) for r in query(queries.inferred_classes(identifier))) if c not in hidden],
        owners=[_linked(r) for r in query(queries.source_owners(identifier))],
        buildings=[_linked(r) for r in query(queries.source_buildings(identifier))],
        storages=[_linked(r) for r in query(queries.source_storages(identifier))],
        zone=zone[0] if zone else None,
    )


def get_indicators() -> Indicators:
    rows = query(queries.indicators())
    by_kind = [
        KindIndicator(
            kind=row["kind"], renewable=row["renewable"] == "true", count=int(row["count"]),
            total_power_kw=round(float(row["totalPower"]), 2), annual_production_mwh=round(float(row["totalProduction"]), 2),
        )
        for row in rows
    ]
    production = sum(float(row["totalProduction"]) for row in rows)
    renewable = sum(float(row["totalProduction"]) for row in rows if row["renewable"] == "true")
    co2 = sum(float(row["weightedCo2"]) for row in rows)
    return Indicators(
        count=sum(int(row["count"]) for row in rows), total_power_kw=round(sum(float(row["totalPower"]) for row in rows), 2),
        annual_production_mwh=round(production, 2),
        renewable_share_percent=round(100 * renewable / production, 1) if production else 0,
        average_co2_g_per_kwh=round(co2 / production, 1) if production else 0,
        by_kind=by_kind,
    )


def get_options() -> Options:
    def options(kind: str) -> list[Linked]:
        return [_linked(row) for row in query(queries.options(kind))]
    return Options(buildings=options("Batiment"), storages=options("Stockage"), zones=options("Zone"))


def _checked(identifiers: list[str], kind: str, label: str) -> list[str]:
    unique = list(dict.fromkeys(identifiers))
    for identifier in unique:
        if not is_identifier(identifier) or not ask(queries.is_a(identifier, kind)):
            raise HTTPException(status_code=422, detail=f"{label} inconnu(e) : {identifier}.")
    return unique


def _data(data: SourceInput) -> dict:
    values = {FIELDS[field]: value for field, value in data.model_dump().items() if field in FIELDS}
    values["typeCombustible"] = _clean(values["typeCombustible"])
    for prop, kinds in queries.SPECIFIC.items():
        # Le domaine de ces propriétés est un type précis : les utiliser sur un autre type rendrait
        # l'ontologie incohérente (ex. typeCombustible sur une éolienne, renouvelable et non renouvelable sont disjointes).
        if values.get(prop) is not None and data.kind not in kinds:
            raise HTTPException(status_code=422, detail=f"{LABELS[prop]} ne s’applique pas à ce type de source.")
    owner = _checked([data.owner], "Batiment", "Bâtiment") if _clean(data.owner) else []
    zone = _checked([data.zone], "Zone", "Zone") if _clean(data.zone) else []
    return {
        **values, "name": data.name.strip(), "owner": owner[0] if owner else None, "zone": zone[0] if zone else None,
        "buildings": _checked(data.buildings, "Batiment", "Bâtiment"),
        "storages": _checked(data.storages, "Stockage", "Stockage"),
    }


def _new_identifier(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", normalize(name)) or ["source"]
    base = "source" + "".join(word.capitalize() for word in words)
    identifier, suffix = base, 2
    while ask(queries.exists(identifier)):
        identifier, suffix = f"{base}{suffix}", suffix + 1
    return identifier


def _existing(identifier: str) -> str:
    identifier = _safe_identifier(identifier)
    if not _is_source(identifier):
        raise HTTPException(status_code=404, detail="Source d’énergie introuvable.")
    return identifier


def create_source(data: SourceInput) -> Mutation:
    values = _data(data)
    identifier = _new_identifier(values["name"])
    sparql = queries.create_source(identifier, data.kind, values)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def update_source(identifier: str, data: SourceInput) -> Mutation:
    identifier = _existing(identifier)
    sparql = queries.update_source(identifier, data.kind, _data(data))
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def delete_source(identifier: str) -> Mutation:
    identifier = _existing(identifier)
    if ask(queries.has_interventions(identifier)):
        raise HTTPException(
            status_code=409,
            detail="Cette source a un historique de maintenance : supprimez d’abord ses interventions.",
        )
    sparql = queries.delete_source(identifier)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)
