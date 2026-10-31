"""Requêtes SPARQL de la feature Stockage (lecture, filtrage, indicateurs et CRUD)."""

from app.shared.sparql import NAMESPACE, PREFIXES, most_specific_kind, number, string

# Types de stockage proposés dans les filtres et le formulaire (Batterie inclut ses sous-classes par inférence).
STORAGE_CLASSES = ("Batterie", "BatterieLithium", "BatteriePlomb", "SuperCondensateur", "StockageHydrogene")
BATTERY_CLASSES = ("Batterie", "BatterieLithium", "BatteriePlomb")
# Seuils du niveau de charge (en %) utilisés par le filtre « charge ».
CHARGE_LEVELS = {"faible": "?charge < 50", "moyen": "?charge >= 50 && ?charge < 80", "eleve": "?charge >= 80"}


def kind_within(variable: str, root: str) -> str:
    """Comme most_specific_kind, mais limité à la hiérarchie d'une classe racine (ex. :Stockage).

    Évite d'afficher comme « type » les classes définies d'autres features (EquipementEntretenu...).
    """
    return f"""?{variable} a ?kindClass .
  ?kindClass rdfs:subClassOf :{root} .
  FILTER(STRSTARTS(STR(?kindClass), "{NAMESPACE}"))
  FILTER NOT EXISTS {{
    ?{variable} a ?narrower .
    ?narrower rdfs:subClassOf ?kindClass, :{root} .
    FILTER(?narrower != ?kindClass && STRSTARTS(STR(?narrower), "{NAMESPACE}"))
  }}
  BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)"""


def _text_filter(variable: str, text: str | None) -> str:
    if not text:
        return ""
    return f"FILTER(CONTAINS(LCASE(STR(?{variable})), LCASE({string(text)})))"


def _storages(pattern: str, extra: str = "") -> str:
    """Stockages avec leurs caractéristiques et l'énergie disponible calculée en SPARQL (BIND)."""
    return PREFIXES + f"""
SELECT ?storage ?name (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       ?capacity ?charge ?available ?rechargeTime ?cycles ?lifetime ?year ?installationCost
       (COUNT(DISTINCT ?source) AS ?sourceCount) (COUNT(DISTINCT ?building) AS ?buildingCount) WHERE {{
  {pattern}
  ?storage a :Stockage .
  OPTIONAL {{ ?storage :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?storage), "#")) AS ?name)
  OPTIONAL {{ ?storage :capacite ?capacity }}
  OPTIONAL {{ ?storage :niveauCharge ?charge }}
  OPTIONAL {{ ?storage :tempsRecharge ?rechargeTime }}
  OPTIONAL {{ ?storage :nombreCyclesCharge ?cycles }}
  OPTIONAL {{ ?storage :dureeVie ?lifetime }}
  OPTIONAL {{ ?storage :anneeInstallation ?year }}
  OPTIONAL {{ ?storage :coutInstallation ?installationCost }}
  OPTIONAL {{ ?source :stockeDans ?storage }}
  OPTIONAL {{ ?storage :alimente ?building }}
  BIND(?capacity * ?charge / 100 AS ?available)
  {kind_within("storage", "Stockage")}
  {extra}
}}
GROUP BY ?storage ?name ?capacity ?charge ?available ?rechargeTime ?cycles ?lifetime ?year ?installationCost
ORDER BY DESC(?capacity) ?name
"""


def storage_list(
    kind: str | None = None, text: str | None = None, min_capacity: float | None = None, charge: str | None = None,
) -> str:
    pattern = ""
    if kind in STORAGE_CLASSES:
        # Inférence : un individu déclaré BatterieLithium est aussi une Batterie (rdfs:subClassOf).
        pattern = f"?storage a :{kind} ."
    filters = _text_filter("name", text)
    if min_capacity is not None:
        filters += f"\n  FILTER(?capacity >= {number(min_capacity)})"
    if charge in CHARGE_LEVELS:
        filters += f"\n  FILTER(BOUND(?charge) && {CHARGE_LEVELS[charge]})"
    return _storages(pattern, filters)


def storage_detail(identifier: str) -> str:
    return _storages(f"VALUES ?storage {{ :{identifier} }}")


def inferred_classes(identifier: str) -> str:
    """Toutes les classes de l'individu dans le graphe inféré (sous-classes, classes définies...)."""
    return PREFIXES + f"""
SELECT DISTINCT ?class WHERE {{
  :{identifier} a ?class .
  FILTER(STRSTARTS(STR(?class), "{NAMESPACE}"))
}}
ORDER BY ?class
"""


def _linked(pattern: str) -> str:
    return PREFIXES + f"""
SELECT ?element (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       (SAMPLE(?powerValue) AS ?power) (SAMPLE(?consumptionValue) AS ?consumption) WHERE {{
  {pattern}
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?label)
  OPTIONAL {{ ?element :puissance ?powerValue }}
  OPTIONAL {{ ?element :consommation ?consumptionValue }}
  {most_specific_kind("element")}
}}
GROUP BY ?element
ORDER BY ?name
"""


def storage_sources(identifier: str) -> str:
    return _linked(f"?element :stockeDans :{identifier} .")


def storage_buildings(identifier: str) -> str:
    return _linked(f":{identifier} :alimente ?element .")


def storage_buildings_inferred(identifier: str) -> str:
    # estAlimentePar n'est pas saisi : il est déduit de alimente (owl:inverseOf), et
    # BatimentAvecStockage ≡ Batiment ⊓ ∃estAlimentePar.Stockage est une classe définie.
    return PREFIXES + f"""
SELECT ?building WHERE {{
  ?building :estAlimentePar :{identifier} ; a :BatimentAvecStockage .
}}
"""


def indicators() -> str:
    """Indicateurs globaux : agrégats SPARQL (COUNT, SUM, AVG) par type de stockage."""
    return PREFIXES + f"""
SELECT ?kind (COUNT(DISTINCT ?storage) AS ?count) (SUM(?capacity) AS ?totalCapacity)
       (SUM(?capacity * ?charge / 100) AS ?totalAvailable) (AVG(?charge) AS ?averageCharge) WHERE {{
  ?storage a :Stockage ; :capacite ?capacity ; :niveauCharge ?charge .
  {kind_within("storage", "Stockage")}
}}
GROUP BY ?kind
ORDER BY DESC(?totalCapacity)
"""


def options(kind: str) -> str:
    """Individus d'une classe (sources ou bâtiments) proposés dans le formulaire."""
    return PREFIXES + f"""
SELECT ?element (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds) WHERE {{
  ?element a :{kind} .
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?label)
  {most_specific_kind("element")}
}}
GROUP BY ?element
ORDER BY ?name
"""


def is_a(identifier: str, kind: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} a :{kind} }}"


def exists(identifier: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} ?p ?o }}"


def has_interventions(identifier: str) -> str:
    return PREFIXES + f"ASK {{ ?intervention :concerne :{identifier} }}"


def _storage_triples(identifier: str, data: dict) -> str:
    triples = [f":{identifier} :nom {string(data['name'])} ."]
    numbers = {
        "capacite": data["capacity"], "niveauCharge": data["charge"], "tempsRecharge": data.get("recharge_time"),
        "dureeVie": data.get("lifetime"), "coutInstallation": data.get("installation_cost"),
    }
    for prop, value in numbers.items():
        if value is not None:
            literal = f'"{int(value)}"^^xsd:integer' if prop == "dureeVie" else number(value)
            triples.append(f":{identifier} :{prop} {literal} .")
    if data.get("installation_year") is not None:
        triples.append(f':{identifier} :anneeInstallation "{int(data["installation_year"])}"^^xsd:integer .')
    if data.get("cycles") is not None:
        triples.append(f':{identifier} :nombreCyclesCharge "{int(data["cycles"])}"^^xsd:integer .')
    triples += [f":{source} :stockeDans :{identifier} ." for source in data.get("sources", [])]
    triples += [f":{identifier} :alimente :{building} ." for building in data.get("buildings", [])]
    return "\n  ".join(triples)


def create_storage(identifier: str, kind: str, data: dict) -> str:
    return PREFIXES + f"""INSERT DATA {{
  :{identifier} a :{kind}, owl:NamedIndividual .
  {_storage_triples(identifier, data)}
}}"""


STORAGE_PROPERTIES = ("nom", "capacite", "niveauCharge", "tempsRecharge", "dureeVie", "coutInstallation",
                      "anneeInstallation", "nombreCyclesCharge")


def update_storage(identifier: str, kind: str, data: dict) -> str:
    deleted = " ".join(f":{prop} ?old{index} ;" for index, prop in enumerate(STORAGE_PROPERTIES))
    optional = "\n  ".join(
        f"OPTIONAL {{ :{identifier} :{prop} ?old{index} }}" for index, prop in enumerate(STORAGE_PROPERTIES)
    )
    classes = " ".join(f":{c}" for c in (*STORAGE_CLASSES, "Stockage"))
    return PREFIXES + f"""DELETE {{
  :{identifier} a ?oldClass ; {deleted} :alimente ?oldBuilding .
  ?oldSource :stockeDans :{identifier} .
}}
INSERT {{
  :{identifier} a :{kind} .
  {_storage_triples(identifier, data)}
}}
WHERE {{
  VALUES ?oldClass {{ {classes} }}
  :{identifier} a ?oldClass .
  {optional}
  OPTIONAL {{ :{identifier} :alimente ?oldBuilding }}
  OPTIONAL {{ ?oldSource :stockeDans :{identifier} }}
}}"""


def delete_storage(identifier: str) -> str:
    return PREFIXES + f"""DELETE WHERE {{ :{identifier} ?p ?o }} ;
DELETE WHERE {{ ?s ?p :{identifier} }}"""
