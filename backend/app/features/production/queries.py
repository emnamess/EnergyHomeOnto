"""Requêtes SPARQL de la feature Production (lecture, filtrage, indicateurs et CRUD des sources d'énergie)."""

from app.shared.sparql import NAMESPACE, PREFIXES, most_specific_kind, number, string

# Types concrets de source : chaque individu en déclare exactement un (classes disjointes deux à deux).
SOURCE_CLASSES = ("PanneauSolaire", "Eolienne", "CentraleHydraulique", "CentraleThermique", "GroupeElectrogene")
FOSSIL_CLASSES = ("CentraleThermique", "GroupeElectrogene")  # sous-classes de SourceNonRenouvelable
# Caractéristiques techniques propres à un type, d'après le domaine des propriétés dans l'ontologie.
SPECIFIC = {
    "surfacePanneau": ("PanneauSolaire",), "inclinaison": ("PanneauSolaire",),
    "diametreRotor": ("Eolienne",), "hauteurMat": ("Eolienne",), "vitesseVentDemarrage": ("Eolienne",),
    "debitEau": ("CentraleHydraulique",), "typeCombustible": FOSSIL_CLASSES,
}
NUMBERS = ("puissance", "rendement", "productionAnnuelle", "emissionCO2", "coutInstallation",
           "surfacePanneau", "inclinaison", "diametreRotor", "hauteurMat", "vitesseVentDemarrage", "debitEau")
INTEGERS = ("dureeVie", "anneeInstallation")
SOURCE_PROPERTIES = ("nom", *NUMBERS, *INTEGERS, "typeCombustible")


def _values(variable: str, classes: tuple[str, ...]) -> str:
    return f"VALUES ?{variable} {{ " + " ".join(f":{c}" for c in classes) + " }"


def _text_filter(variable: str, text: str | None) -> str:
    if not text:
        return ""
    return f"FILTER(CONTAINS(LCASE(STR(?{variable})), LCASE({string(text)})))"


def _sources(pattern: str, extra: str = "") -> str:
    """Sources avec leurs caractéristiques ; renouvelable est déduit (rdfs:subClassOf SourceRenouvelable)."""
    optional = "\n  ".join(f"OPTIONAL {{ ?source :{prop} ?{prop} }}" for prop in (*NUMBERS, *INTEGERS, "typeCombustible"))
    columns = " ".join(f"?{prop}" for prop in (*NUMBERS, *INTEGERS, "typeCombustible"))
    return PREFIXES + f"""
SELECT ?source ?name ?kind ?renewable {columns}
       (SAMPLE(?ownerLabel) AS ?owner) (COUNT(DISTINCT ?building) AS ?buildingCount)
       (COUNT(DISTINCT ?storage) AS ?storageCount) WHERE {{
  {pattern}
  {_values("kindClass", SOURCE_CLASSES)}
  ?source a ?kindClass .
  BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)
  OPTIONAL {{ ?source :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?source), "#")) AS ?name)
  BIND(EXISTS {{ ?source a :SourceRenouvelable }} AS ?renewable)
  {optional}
  OPTIONAL {{ ?ownerBuilding :possede ?source . OPTIONAL {{ ?ownerBuilding :nom ?ownerName }}
             BIND(COALESCE(?ownerName, STRAFTER(STR(?ownerBuilding), "#")) AS ?ownerLabel) }}
  OPTIONAL {{ ?source :alimente ?building }}
  OPTIONAL {{ ?source :stockeDans ?storage }}
  {extra}
}}
GROUP BY ?source ?name ?kind ?renewable {columns}
ORDER BY DESC(?puissance) ?name
"""


def source_list(
    kind: str | None = None, text: str | None = None, min_power: float | None = None, renewable: bool | None = None,
) -> str:
    pattern = f"?source a :{kind} ." if kind in SOURCE_CLASSES else ""
    if renewable is not None:
        # Inférence : PanneauSolaire, Eolienne et CentraleHydraulique sont des sous-classes de SourceRenouvelable.
        pattern += f"\n  ?source a :{'SourceRenouvelable' if renewable else 'SourceNonRenouvelable'} ."
    filters = _text_filter("name", text)
    if min_power is not None:
        filters += f"\n  FILTER(?puissance >= {number(min_power)})"
    return _sources(pattern, filters)


def source_detail(identifier: str) -> str:
    return _sources(f"VALUES ?source {{ :{identifier} }}")


def inferred_classes(identifier: str) -> str:
    return PREFIXES + f"""
SELECT DISTINCT ?class WHERE {{
  :{identifier} a ?class .
  FILTER(STRSTARTS(STR(?class), "{NAMESPACE}"))
}}
ORDER BY ?class
"""


def _linked(pattern: str) -> str:
    return PREFIXES + f"""
SELECT ?element (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds) WHERE {{
  {pattern}
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?label)
  {most_specific_kind("element")}
}}
GROUP BY ?element
ORDER BY ?name
"""


def source_owners(identifier: str) -> str:
    return _linked(f"?element :possede :{identifier} .")


def source_buildings(identifier: str) -> str:
    return _linked(f":{identifier} :alimente ?element .")


def source_storages(identifier: str) -> str:
    return _linked(f":{identifier} :stockeDans ?element .")


def source_zone(identifier: str) -> str:
    # estSitueDans est transitive : on ne garde que la zone déclarée la plus précise.
    return _linked(f""":{identifier} :estSitueDans ?element .
  FILTER NOT EXISTS {{ :{identifier} :estSitueDans ?inner . ?inner :estSitueDans ?element . FILTER(?inner != ?element) }}""")


def indicators() -> str:
    """Indicateurs globaux : agrégats SPARQL (COUNT, SUM) par type de source."""
    return PREFIXES + f"""
SELECT ?kind ?renewable (COUNT(DISTINCT ?source) AS ?count) (SUM(?power) AS ?totalPower)
       (SUM(COALESCE(?production, 0)) AS ?totalProduction)
       (SUM(COALESCE(?production, 0) * COALESCE(?co2, 0)) AS ?weightedCo2) WHERE {{
  {_values("kindClass", SOURCE_CLASSES)}
  ?source a ?kindClass ; :puissance ?power .
  BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)
  BIND(EXISTS {{ ?source a :SourceRenouvelable }} AS ?renewable)
  OPTIONAL {{ ?source :productionAnnuelle ?production }}
  OPTIONAL {{ ?source :emissionCO2 ?co2 }}
}}
GROUP BY ?kind ?renewable
ORDER BY DESC(?totalProduction)
"""


def options(kind: str) -> str:
    """Individus d'une classe (bâtiments, stockages, zones) proposés dans le formulaire."""
    return _linked(f"?element a :{kind} .")


def is_a(identifier: str, kind: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} a :{kind} }}"


def exists(identifier: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} ?p ?o }}"


def has_interventions(identifier: str) -> str:
    return PREFIXES + f"ASK {{ ?intervention :concerne :{identifier} }}"


def _source_triples(identifier: str, data: dict) -> str:
    triples = [f":{identifier} :nom {string(data['name'])} ."]
    for prop in NUMBERS:
        if data.get(prop) is not None:
            triples.append(f":{identifier} :{prop} {number(data[prop])} .")
    for prop in INTEGERS:
        if data.get(prop) is not None:
            triples.append(f':{identifier} :{prop} "{int(data[prop])}"^^xsd:integer .')
    if data.get("typeCombustible"):
        triples.append(f":{identifier} :typeCombustible {string(data['typeCombustible'])} .")
    if data.get("owner"):
        triples.append(f":{data['owner']} :possede :{identifier} .")
    if data.get("zone"):
        triples.append(f":{identifier} :estSitueDans :{data['zone']} .")
    triples += [f":{identifier} :alimente :{building} ." for building in data.get("buildings", [])]
    triples += [f":{identifier} :stockeDans :{storage} ." for storage in data.get("storages", [])]
    return "\n  ".join(triples)


def create_source(identifier: str, kind: str, data: dict) -> str:
    return PREFIXES + f"""INSERT DATA {{
  :{identifier} a :{kind}, owl:NamedIndividual .
  {_source_triples(identifier, data)}
}}"""


def update_source(identifier: str, kind: str, data: dict) -> str:
    deleted = " ".join(f":{prop} ?old{index} ;" for index, prop in enumerate(SOURCE_PROPERTIES))
    optional = "\n  ".join(
        f"OPTIONAL {{ :{identifier} :{prop} ?old{index} }}" for index, prop in enumerate(SOURCE_PROPERTIES)
    )
    return PREFIXES + f"""DELETE {{
  :{identifier} a ?oldClass ; {deleted} :alimente ?oldBuilding ; :stockeDans ?oldStorage ; :estSitueDans ?oldZone .
  ?oldOwner :possede :{identifier} .
}}
INSERT {{
  :{identifier} a :{kind} .
  {_source_triples(identifier, data)}
}}
WHERE {{
  {_values("oldClass", SOURCE_CLASSES)}
  :{identifier} a ?oldClass .
  {optional}
  OPTIONAL {{ :{identifier} :alimente ?oldBuilding }}
  OPTIONAL {{ :{identifier} :stockeDans ?oldStorage }}
  OPTIONAL {{ :{identifier} :estSitueDans ?oldZone }}
  OPTIONAL {{ ?oldOwner :possede :{identifier} }}
}}"""


def delete_source(identifier: str) -> str:
    return PREFIXES + f"""DELETE WHERE {{ :{identifier} ?p ?o }} ;
DELETE WHERE {{ ?s ?p :{identifier} }}"""
