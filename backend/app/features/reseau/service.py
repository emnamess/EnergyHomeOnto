import re

from fastapi import HTTPException

from app.features.reseau import queries
from app.features.reseau.schemas import (
    Indicators, KindIndicator, Mutation, NetworkDetail, NetworkInput, NetworkElement, Option, Options, RelatedElement,
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


def _element(row: dict[str, str]) -> NetworkElement:
    return NetworkElement(
        id=local_name(row["element"]), name=row["name"], kind=row["kinds"],
        length=_float(row, "length"), voltage=_float(row, "voltage"), section=_float(row, "section"),
        loss_rate=_float(row, "lossRate"), underground=row.get("underground", "").lower() == "true" if "underground" in row else None,
        transformation_power=_float(row, "transformationPower"), meter_identifier=row.get("meterIdentifier"),
        reading_frequency=_integer(row, "readingFrequency"), installation_year=_integer(row, "year"),
        lifetime_years=_integer(row, "lifetime"), installation_cost=_float(row, "installationCost"),
        related_count=int(row.get("relatedCount", 0)),
    )


def _related(row: dict[str, str]) -> RelatedElement:
    return RelatedElement(id=local_name(row["element"]), name=row["name"], kind=row["kind"])


def list_elements(kind: str | None = None, text: str | None = None, min_voltage: float | None = None,
                  max_voltage: float | None = None, underground: bool | None = None) -> list[NetworkElement]:
    if min_voltage is not None and max_voltage is not None and min_voltage > max_voltage:
        raise HTTPException(status_code=422, detail="La tension minimale doit être inférieure à la tension maximale.")
    return [_element(row) for row in query(queries.element_list(kind, text.strip() if text else None,
                                                               min_voltage, max_voltage, underground))]


def _network_kind(identifier: str) -> bool:
    return any(ask(queries.is_kind(identifier, kind)) for kind in queries.NETWORK_CLASSES)


def get_element(identifier: str) -> NetworkDetail:
    identifier = _safe_identifier(identifier)
    if not _network_kind(identifier):
        raise HTTPException(status_code=404, detail="Élément réseau introuvable.")
    rows = query(queries.element_detail(identifier))
    if not rows:
        raise HTTPException(status_code=404, detail="Élément réseau introuvable.")
    element = _element({**rows[0], "element": f"#{identifier}"})
    specific = set(element.kind.split(", "))
    inferred = [local_name(row["class"]) for row in query(queries.inferred_classes(identifier))]
    return NetworkDetail(
        **element.model_dump(), inferred_classes=[kind for kind in inferred if kind not in specific],
        relationships=[_related(row) for row in query(queries.relationships(identifier))],
        managers=[_related(row) for row in query(queries.managers(identifier))],
    )


def get_indicators() -> Indicators:
    rows = query(queries.indicators())
    items = [KindIndicator(kind=row["kind"], count=int(row["count"])) for row in rows]
    total = query(queries.total_count())
    return Indicators(count=int(total[0]["count"]) if total else 0, by_kind=items)


def _options(kind: str) -> list[Option]:
    return [Option(id=local_name(row["element"]), name=row["name"], kind=row["kinds"])
            for row in query(queries.options(kind))]


def get_options() -> Options:
    return Options(
        kinds=list(queries.NETWORK_CLASSES), lines=_options("LigneElectrique"),
        equipment=_options("EquipementReseau"), managers=_options("GestionnaireReseau"),
        buildings=_options("Batiment"), sources=_options("SourceEnergie"), storages=_options("Stockage"),
    )


def _checked(identifiers: list[str], kind: str, label: str) -> list[str]:
    unique = list(dict.fromkeys(identifiers))
    for identifier in unique:
        if not is_identifier(identifier) or not ask(queries.is_kind(identifier, kind)):
            raise HTTPException(status_code=422, detail=f"{label} inconnu(e) : {identifier}.")
    return unique


def _data(data: NetworkInput) -> dict:
    line = data.kind in queries.LINE_CLASSES
    network_equipment = data.kind in queries.EQUIPMENT_CLASSES
    allowed = {
        "length": line,
        "voltage": line or data.kind == "PosteTransformation",
        "section": line,
        "loss_rate": line,
        "underground": data.kind in ("LigneElectrique", "LigneHauteTension", "LigneMoyenneTension", "LigneBasseTension", "LigneSouterraine"),
        "transformation_power": data.kind == "PosteTransformation",
        "meter_identifier": data.kind == "CompteurIntelligent",
        "reading_frequency": data.kind == "CompteurIntelligent",
        "lifetime_years": network_equipment,
        "installation_cost": network_equipment,
    }
    labels = {
        "length": "La longueur ne concerne que les lignes", "section": "La section ne concerne que les lignes",
        "loss_rate": "Le taux de pertes ne concerne que les lignes", "underground": "Le statut souterrain ne concerne que les lignes",
        "transformation_power": "La puissance de transformation ne concerne que les postes de transformation",
        "meter_identifier": "L’identifiant de compteur ne concerne que les compteurs intelligents",
        "reading_frequency": "La fréquence de relevé ne concerne que les compteurs intelligents",
        "voltage": "La tension ne concerne que les lignes et les postes de transformation",
        "lifetime_years": "La durée de vie ne concerne que les équipements du réseau",
        "installation_cost": "Le coût d’installation ne concerne que les équipements du réseau",
    }
    for field, applicable in allowed.items():
        if getattr(data, field) is not None and not applicable:
            raise HTTPException(status_code=422, detail=labels[field] + ".")
    if data.related and not line:
        raise HTTPException(status_code=422, detail="Les relations directes ne concernent que les lignes électriques.")
    if data.kind == "LigneSouterraine" and data.underground is not True:
        raise HTTPException(status_code=422, detail="Une ligne souterraine doit avoir le statut souterrain.")
    return {
        **data.model_dump(), "name": data.name.strip(),
        "related": _checked_network_relations(data.related),
        "managers": _checked(data.managers, "GestionnaireReseau", "Gestionnaire réseau"),
    }


def _checked_network_relations(identifiers: list[str]) -> list[str]:
    unique = list(dict.fromkeys(identifiers))
    allowed = (*queries.NETWORK_CLASSES, "Batiment", "SourceEnergie", "Stockage")
    for identifier in unique:
        if not is_identifier(identifier) or not any(ask(queries.is_kind(identifier, kind)) for kind in allowed):
            raise HTTPException(status_code=422, detail=f"Entité liée inconnue ou incompatible : {identifier}.")
    return unique


def _new_identifier(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", normalize(name)) or ["reseau"]
    base = "reseau" + "".join(word.capitalize() for word in words)
    identifier, suffix = base, 2
    while ask(queries.exists(identifier)):
        identifier, suffix = f"{base}{suffix}", suffix + 1
    return identifier


def create_element(data: NetworkInput) -> Mutation:
    values = _data(data)
    identifier = _new_identifier(values["name"])
    sparql = queries.create_element(identifier, data.kind, values)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def _existing(identifier: str) -> str:
    identifier = _safe_identifier(identifier)
    if not _network_kind(identifier):
        raise HTTPException(status_code=404, detail="Élément réseau introuvable.")
    return identifier


def update_element(identifier: str, data: NetworkInput) -> Mutation:
    identifier = _existing(identifier)
    values = _data(data)
    sparql = queries.update_element(identifier, data.kind, values)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def delete_element(identifier: str) -> Mutation:
    identifier = _existing(identifier)
    if ask(queries.has_interventions(identifier)):
        raise HTTPException(status_code=409, detail="Cet équipement réseau possède un historique de maintenance.")
    sparql = queries.delete_element(identifier)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)
