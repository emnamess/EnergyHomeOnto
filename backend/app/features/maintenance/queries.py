"""Requêtes SPARQL de la feature Maintenance (lecture, filtrage et CRUD)."""

import datetime

from rdflib import Literal
from rdflib.namespace import XSD

from app.shared.sparql import PREFIXES, most_specific_kind, number, string

EQUIPMENT_CATEGORIES = ("SourceEnergie", "Stockage", "EquipementReseau")
INTERVENTION_CLASSES = ("InterventionPreventive", "InterventionCorrective")


def _values(variable: str, classes: tuple[str, ...], kind: str | None) -> str:
    selected = [kind] if kind in classes else list(classes)
    return f"VALUES ?{variable} {{ " + " ".join(f":{c}" for c in selected) + " }"


def _text_filter(variable: str, text: str | None) -> str:
    if not text:
        return ""
    return f"FILTER(CONTAINS(LCASE(STR(?{variable})), LCASE({string(text)})))"


def _date(value: datetime.date) -> str:
    return Literal(value, datatype=XSD.date).n3()


def _equipment(pattern: str, year: int, extra: str = "") -> str:
    """Équipements avec âge et durée de vie restante, calculés à partir de l'année de référence."""
    return PREFIXES + f"""
SELECT ?equipment ?name ?category (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       ?year ?lifetime ?age ?remaining ?installationCost (COUNT(DISTINCT ?intervention) AS ?interventionCount) WHERE {{
  {pattern}
  ?equipment a ?class .
  BIND(STRAFTER(STR(?class), "#") AS ?category)
  OPTIONAL {{ ?equipment :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?equipment), "#")) AS ?name)
  OPTIONAL {{ ?equipment :anneeInstallation ?year }}
  OPTIONAL {{ ?equipment :dureeVie ?lifetime }}
  OPTIONAL {{ ?equipment :coutInstallation ?installationCost }}
  # aSubi n'est pas saisi : il est déduit de concerne (owl:inverseOf).
  OPTIONAL {{ ?equipment :aSubi ?intervention }}
  BIND({year} - ?year AS ?age)
  BIND(?year + ?lifetime - {year} AS ?remaining)
  {most_specific_kind("equipment")}
  {extra}
}}
GROUP BY ?equipment ?name ?category ?year ?lifetime ?age ?remaining ?installationCost
ORDER BY ASC(COALESCE(?remaining, 9999)) ?name
"""


def equipment_list(year: int, category: str | None = None, text: str | None = None, horizon: int | None = None) -> str:
    filters = _text_filter("name", text)
    if horizon is not None:
        # Équipements dont la fin de vie prévue tombe dans les `horizon` prochaines années (ou déjà dépassée).
        filters += f"\n  FILTER(BOUND(?remaining) && ?remaining <= {int(horizon)})"
    return _equipment(_values("class", EQUIPMENT_CATEGORIES, category), year, filters)


def equipment_detail(identifier: str, year: int) -> str:
    return _equipment(f"{_values('class', EQUIPMENT_CATEGORIES, None)}\n  VALUES ?equipment {{ :{identifier} }}", year)


def _interventions(pattern: str, extra: str = "") -> str:
    return PREFIXES + f"""
SELECT ?intervention ?kind ?date ?cost ?description ?provider ?equipment ?equipmentName WHERE {{
  {pattern}
  ?intervention a ?class ; :concerne ?equipment ; :dateIntervention ?date ; :descriptionIntervention ?description .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ ?intervention :coutIntervention ?cost }}
  OPTIONAL {{ ?intervention :prestataire ?provider }}
  OPTIONAL {{ ?equipment :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?equipment), "#")) AS ?equipmentName)
  BIND(CONCAT(?description, " ", COALESCE(?provider, ""), " ", ?equipmentName) AS ?searchText)
  {extra}
}}
ORDER BY DESC(?date) ?intervention
"""


def intervention_list(kind: str | None = None, text: str | None = None) -> str:
    return _interventions(_values("class", INTERVENTION_CLASSES, kind), _text_filter("searchText", text))


def intervention_detail(identifier: str) -> str:
    return _interventions(f"{_values('class', INTERVENTION_CLASSES, None)}\n  VALUES ?intervention {{ :{identifier} }}")


def equipment_interventions(identifier: str) -> str:
    return _interventions(f"{_values('class', INTERVENTION_CLASSES, None)}\n  VALUES ?equipment {{ :{identifier} }}")


def is_equipment(identifier: str) -> str:
    # EquipementMaintenable ≡ SourceEnergie ⊔ Stockage ⊔ EquipementReseau : appartenance déduite par le raisonneur.
    return PREFIXES + f"ASK {{ :{identifier} a :EquipementMaintenable }}"


def intervention_exists(identifier: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} ?p ?o }}"


def _intervention_triples(
    identifier: str, equipment: str, date: datetime.date, cost: float | None, description: str, provider: str | None,
) -> str:
    triples = [
        f":{identifier} :concerne :{equipment} .",
        f":{identifier} :dateIntervention {_date(date)} .",
        f":{identifier} :descriptionIntervention {string(description)} .",
    ]
    if cost is not None:
        triples.append(f":{identifier} :coutIntervention {number(cost)} .")
    if provider:
        triples.append(f":{identifier} :prestataire {string(provider)} .")
    return "\n  ".join(triples)


def create_intervention(
    identifier: str, kind: str, equipment: str, date: datetime.date, cost: float | None, description: str, provider: str | None,
) -> str:
    return PREFIXES + f"""INSERT DATA {{
  :{identifier} a :{kind}, owl:NamedIndividual .
  {_intervention_triples(identifier, equipment, date, cost, description, provider)}
}}"""


def update_intervention(
    identifier: str, kind: str, equipment: str, date: datetime.date, cost: float | None, description: str, provider: str | None,
) -> str:
    return PREFIXES + f"""DELETE {{
  :{identifier} a ?oldClass ; :concerne ?oldEquipment ; :dateIntervention ?oldDate ; :coutIntervention ?oldCost ;
    :descriptionIntervention ?oldDescription ; :prestataire ?oldProvider .
}}
INSERT {{
  :{identifier} a :{kind} .
  {_intervention_triples(identifier, equipment, date, cost, description, provider)}
}}
WHERE {{
  VALUES ?oldClass {{ {" ".join(f":{c}" for c in INTERVENTION_CLASSES)} }}
  :{identifier} a ?oldClass .
  OPTIONAL {{ :{identifier} :concerne ?oldEquipment }}
  OPTIONAL {{ :{identifier} :dateIntervention ?oldDate }}
  OPTIONAL {{ :{identifier} :coutIntervention ?oldCost }}
  OPTIONAL {{ :{identifier} :descriptionIntervention ?oldDescription }}
  OPTIONAL {{ :{identifier} :prestataire ?oldProvider }}
}}"""


def delete_intervention(identifier: str) -> str:
    return PREFIXES + f"""DELETE WHERE {{ :{identifier} ?p ?o }} ;
DELETE WHERE {{ ?s ?p :{identifier} }}"""
