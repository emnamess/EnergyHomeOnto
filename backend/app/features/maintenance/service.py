import datetime

from fastapi import HTTPException

from app.features.maintenance import queries
from app.features.maintenance.schemas import Equipment, EquipmentDetail, Intervention, InterventionInput, Mutation
from app.shared.rdf_store import ask, query, update
from app.shared.sparql import is_identifier, local_name

# Un équipement dont la fin de vie prévue arrive dans ce nombre d'années est à remplacer.
RENEWAL_HORIZON = 3
# Classes définies de l'ontologie, déduites par le raisonneur à partir des interventions.
MAINTENANCE_CLASSES = ("EquipementEntretenu", "EquipementDejaRepare")


def _safe_identifier(identifier: str) -> str:
    if not is_identifier(identifier):
        raise HTTPException(status_code=404, detail="Identifiant inconnu.")
    return identifier


def _integer(row: dict[str, str], key: str) -> int | None:
    return int(float(row[key])) if key in row else None


def _status(remaining: int | None) -> str:
    if remaining is None:
        return "inconnu"
    if remaining <= 0:
        return "fin-de-vie"
    return "a-remplacer" if remaining <= RENEWAL_HORIZON else "en-service"


def _equipment(row: dict[str, str]) -> Equipment:
    remaining = _integer(row, "remaining")
    kinds = row["kinds"].split(", ")
    return Equipment(
        id=local_name(row["equipment"]), name=row["name"], category=row["category"],
        kind=", ".join(sorted(kind for kind in kinds if kind not in MAINTENANCE_CLASSES)),
        inferred_classes=sorted(kind for kind in kinds if kind in MAINTENANCE_CLASSES),
        installation_year=_integer(row, "year"), lifetime_years=_integer(row, "lifetime"),
        age_years=_integer(row, "age"), remaining_years=remaining, status=_status(remaining),
        intervention_count=int(row.get("interventionCount", 0)),
    )


def _intervention(row: dict[str, str]) -> Intervention:
    date = datetime.date.fromisoformat(row["date"])
    return Intervention(
        id=local_name(row["intervention"]), kind=row["kind"], date=date, planned=date > datetime.date.today(),
        cost=float(row["cost"]) if "cost" in row else None, description=row["description"],
        provider=row.get("provider"), equipment_id=local_name(row["equipment"]), equipment_name=row["equipmentName"],
    )


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def _year() -> int:
    return datetime.date.today().year


def list_equipment(category: str | None = None, text: str | None = None, horizon: int | None = None) -> list[Equipment]:
    return [_equipment(row) for row in query(queries.equipment_list(_year(), category, _clean(text), horizon))]


def get_equipment(identifier: str) -> EquipmentDetail:
    identifier = _safe_identifier(identifier)
    rows = query(queries.equipment_detail(identifier, _year()))
    if not rows:
        raise HTTPException(status_code=404, detail="Équipement introuvable.")
    equipment = _equipment({**rows[0], "equipment": f"#{identifier}"})
    interventions = [_intervention(row) for row in query(queries.equipment_interventions(identifier))]
    return EquipmentDetail(
        **equipment.model_dump(),
        installation_cost=float(rows[0]["installationCost"]) if "installationCost" in rows[0] else None,
        maintenance_cost=sum(item.cost or 0 for item in interventions),
        interventions=interventions,
    )


def list_interventions(kind: str | None = None, text: str | None = None) -> list[Intervention]:
    return [_intervention(row) for row in query(queries.intervention_list(kind, _clean(text)))]


def get_intervention(identifier: str) -> Intervention:
    identifier = _safe_identifier(identifier)
    rows = query(queries.intervention_detail(identifier))
    if not rows:
        raise HTTPException(status_code=404, detail="Intervention introuvable.")
    return _intervention(rows[0])


def _checked_equipment(identifier: str) -> str:
    if not is_identifier(identifier) or not ask(queries.is_equipment(identifier)):
        raise HTTPException(status_code=422, detail="Équipement inconnu.")
    return identifier


def _new_identifier() -> str:
    number = 1
    while ask(queries.intervention_exists(f"intervention{number}")):
        number += 1
    return f"intervention{number}"


def _arguments(data: InterventionInput) -> tuple:
    equipment = _checked_equipment(data.equipment)
    return data.kind, equipment, data.date, data.cost, data.description.strip(), _clean(data.provider)


def create_intervention(data: InterventionInput) -> Mutation:
    arguments = _arguments(data)
    identifier = _new_identifier()
    sparql = queries.create_intervention(identifier, *arguments)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def update_intervention(identifier: str, data: InterventionInput) -> Mutation:
    get_intervention(identifier)
    sparql = queries.update_intervention(identifier, *_arguments(data))
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)


def delete_intervention(identifier: str) -> Mutation:
    get_intervention(identifier)
    sparql = queries.delete_intervention(identifier)
    update(sparql)
    return Mutation(id=identifier, sparql=sparql)
