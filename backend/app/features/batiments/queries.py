"""Requêtes SPARQL de la feature Bâtiments (lecture, filtrage, inférences et CRUD)."""

from app.shared.sparql import NAMESPACE, PREFIXES, most_specific_kind, number, string

BUILDING_CLASSES = (
    "Batiment",
    "Maison",
    "BatimentPublic",
    "Ecole",
    "Hopital",
    "Mairie",
    "BatimentIndustriel",
    "BatimentCommercial",
    "MaisonAutonome",
    "MaisonIntelligente",
    "BatimentAlimenteRenouvelable",
    "BatimentAvecStockage",
    "BatimentEconome",
    "GrosConsommateur",
)

ENERGY_CLASSES = ("A", "B", "C", "D", "E", "F", "G")


def kind_within(variable: str, root: str = "Batiment") -> str:
    """Lie ?kind à la sous-classe la plus précise dans la hiérarchie de :Batiment."""
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


def _buildings(pattern: str, extra: str = "") -> str:
    return PREFIXES + f"""
SELECT ?building ?name (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       ?consumption ?surface ?occupants ?floors ?energyClass ?gridConnected
       ?latitude ?longitude
       (SAMPLE(?ownerLabel) AS ?ownerName) (SAMPLE(?ownerId) AS ?owner)
       (SAMPLE(?zoneLabel) AS ?zoneName) (SAMPLE(?zoneId) AS ?zone)
       (COUNT(DISTINCT ?source) AS ?sourceCount)
       (COUNT(DISTINCT ?equipment) AS ?equipmentCount) WHERE {{
  {pattern}
  ?building a :Batiment .
  OPTIONAL {{ ?building :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?building), "#")) AS ?name)
  OPTIONAL {{ ?building :consommation ?consumption }}
  OPTIONAL {{ ?building :surface ?surface }}
  OPTIONAL {{ ?building :nombreOccupants ?occupants }}
  OPTIONAL {{ ?building :nombreEtages ?floors }}
  OPTIONAL {{ ?building :classeEnergetique ?energyClass }}
  OPTIONAL {{ ?building :estRaccordeReseau ?gridConnected }}
  OPTIONAL {{ ?building :latitude ?latitude }}
  OPTIONAL {{ ?building :longitude ?longitude }}
  OPTIONAL {{
    ?building :appartientA ?ownerIndividual .
    BIND(STRAFTER(STR(?ownerIndividual), "#") AS ?ownerId)
    OPTIONAL {{ ?ownerIndividual :nom ?ownerGivenName }}
    BIND(COALESCE(?ownerGivenName, ?ownerId) AS ?ownerLabel)
  }}
  OPTIONAL {{
    # Localisation directe (Quartier prioritaire si disponible)
    ?building :estSitueDans ?zoneIndividual .
    ?zoneIndividual a ?zoneClass .
    FILTER(?zoneClass IN (:Quartier, :Ville))
    BIND(STRAFTER(STR(?zoneIndividual), "#") AS ?zoneId)
    OPTIONAL {{ ?zoneIndividual :nom ?zoneGivenName }}
    BIND(COALESCE(?zoneGivenName, ?zoneId) AS ?zoneLabel)
  }}
  OPTIONAL {{
    ?source :alimente ?building .
  }}
  OPTIONAL {{
    ?equipment :estInstalleDans ?building .
  }}
  {kind_within("building", "Batiment")}
  {extra}
}}
GROUP BY ?building ?name ?consumption ?surface ?occupants ?floors ?energyClass ?gridConnected ?latitude ?longitude
ORDER BY ?name
"""


def building_list(
    kind: str | None = None,
    text: str | None = None,
    energy_class: str | None = None,
    grid_connected: bool | None = None,
    min_consumption: float | None = None,
    max_consumption: float | None = None,
) -> str:
    pattern = ""
    if kind in BUILDING_CLASSES:
        # Inférence : exploitation des sous-classes et des classes définies (ex: MaisonAutonome)
        pattern = f"?building a :{kind} ."
    filters = _text_filter("name", text)
    if energy_class and energy_class.upper() in ENERGY_CLASSES:
        filters += f"\n  FILTER(BOUND(?energyClass) && STR(?energyClass) = {string(energy_class.upper())})"
    if grid_connected is not None:
        filters += f"\n  FILTER(BOUND(?gridConnected) && ?gridConnected = {str(grid_connected).lower()})"
    if min_consumption is not None:
        filters += f"\n  FILTER(?consumption >= {number(min_consumption)})"
    if max_consumption is not None:
        filters += f"\n  FILTER(?consumption <= {number(max_consumption)})"
    return _buildings(pattern, filters)


def building_detail(identifier: str) -> str:
    return _buildings(f"VALUES ?building {{ :{identifier} }}")


def inferred_classes(identifier: str) -> str:
    """Toutes les classes du bâtiment dans le graphe inféré (ex: MaisonAutonome, BatimentEconome...)."""
    return PREFIXES + f"""
SELECT DISTINCT ?class WHERE {{
  :{identifier} a ?class .
  FILTER(STRSTARTS(STR(?class), "{NAMESPACE}"))
}}
ORDER BY ?class
"""


def building_zones(identifier: str) -> str:
    """Zones dans lesquelles le bâtiment est situé.
    
    Exploite la TRANSITIVITÉ de :estSitueDans :
    si le bâtiment est situé dans un Quartier qui est situé dans une Ville,
    le raisonneur infère que le bâtiment est aussi situé dans la Ville.
    """
    return PREFIXES + f"""
SELECT DISTINCT ?zone ?name ?kind WHERE {{
  :{identifier} :estSitueDans ?zone .
  ?zone a ?zoneClass .
  FILTER(?zoneClass IN (:Quartier, :Ville))
  BIND(STRAFTER(STR(?zoneClass), "#") AS ?kind)
  OPTIONAL {{ ?zone :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?zone), "#")) AS ?name)
}}
ORDER BY DESC(?kind) ?name
"""


def building_owner_inferred(identifier: str) -> str:
    """Propriétaire du bâtiment déduit de l'INVERSE de :appartientA (owl:inverseOf :estProprietaireDe)."""
    return PREFIXES + f"""
SELECT ?owner ?name ?kind ?email ?phone WHERE {{
  ?owner :estProprietaireDe :{identifier} ; a ?class .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ ?owner :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?owner), "#")) AS ?name)
  OPTIONAL {{ ?owner :email ?email }}
  OPTIONAL {{ ?owner :telephone ?phone }}
}}
"""


def building_energy_sources(identifier: str) -> str:
    """Sources d'énergie et stockages alimentant ou possédés par le bâtiment.
    
    Exploite l'inverse :estAlimentePar déduit de :alimente, et la propriété :possede.
    """
    return PREFIXES + f"""
SELECT DISTINCT ?source (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       (SAMPLE(?powerVal) AS ?power) (SAMPLE(?ownedVal) AS ?owned) WHERE {{
  {{
    :{identifier} :possede ?source .
    BIND(true AS ?ownedVal)
  }} UNION {{
    :{identifier} :estAlimentePar ?source .
    BIND(false AS ?ownedVal)
  }} UNION {{
    ?source :alimente :{identifier} .
    BIND(false AS ?ownedVal)
  }}
  OPTIONAL {{ ?source :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?source), "#")) AS ?label)
  OPTIONAL {{ ?source :puissance ?powerVal }}
  {most_specific_kind("source")}
}}
GROUP BY ?source
ORDER BY ?name
"""


def building_equipment(identifier: str) -> str:
    """Équipements (ex: compteurs intelligents) installés dans le bâtiment.
    
    Exploite l'inverse :estEquipeDe déduit de :estInstalleDans.
    """
    return PREFIXES + f"""
SELECT DISTINCT ?equipment (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       (SAMPLE(?meterId) AS ?identifierNumber) WHERE {{
  {{
    ?equipment :estInstalleDans :{identifier} .
  }} UNION {{
    :{identifier} :estEquipeDe ?equipment .
  }}
  OPTIONAL {{ ?equipment :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?equipment), "#")) AS ?label)
  OPTIONAL {{ ?equipment :identifiantCompteur ?meterId }}
  {most_specific_kind("equipment")}
}}
GROUP BY ?equipment
ORDER BY ?name
"""


def building_lines(identifier: str) -> str:
    """Lignes électriques raccordées au bâtiment."""
    return PREFIXES + f"""
SELECT DISTINCT ?line (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds) WHERE {{
  ?line :relie :{identifier} .
  OPTIONAL {{ ?line :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?line), "#")) AS ?label)
  {most_specific_kind("line")}
}}
GROUP BY ?line
ORDER BY ?name
"""


def indicators() -> str:
    """Indicateurs globaux agrégés en SPARQL (COUNT, AVG, SUM, répartition par classe énergétique)."""
    return PREFIXES + f"""
SELECT (COUNT(DISTINCT ?building) AS ?totalCount)
       (AVG(?consumption) AS ?avgConsumption)
       (SUM(?surface) AS ?totalSurface)
       (AVG(?occupants) AS ?avgOccupants) WHERE {{
  ?building a :Batiment .
  OPTIONAL {{ ?building :consommation ?consumption }}
  OPTIONAL {{ ?building :surface ?surface }}
  OPTIONAL {{ ?building :nombreOccupants ?occupants }}
}}
"""


def energy_class_distribution() -> str:
    return PREFIXES + f"""
SELECT ?energyClass (COUNT(DISTINCT ?building) AS ?count) WHERE {{
  ?building a :Batiment ; :classeEnergetique ?energyClass .
}}
GROUP BY ?energyClass
ORDER BY ?energyClass
"""


def options(kind: str) -> str:
    """Individus d'une classe donnés comme options de sélection pour le formulaire."""
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


def exists(identifier: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} ?p ?o }}"


def is_a(identifier: str, kind: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} a :{kind} }}"


def _building_triples(identifier: str, kind: str, data: dict) -> str:
    triples = [f":{identifier} :nom {string(data['name'])} ."]
    if data.get("consumption") is not None:
        triples.append(f":{identifier} :consommation {number(data['consumption'])} .")
    if data.get("surface") is not None:
        triples.append(f":{identifier} :surface {number(data['surface'])} .")
    if data.get("occupants") is not None:
        triples.append(f':{identifier} :nombreOccupants "{int(data["occupants"])}"^^xsd:integer .')
    if data.get("floors") is not None:
        triples.append(f':{identifier} :nombreEtages "{int(data["floors"])}"^^xsd:integer .')
    if data.get("energy_class"):
        triples.append(f":{identifier} :classeEnergetique {string(data['energy_class'].upper())} .")
    if data.get("grid_connected") is not None:
        triples.append(f':{identifier} :estRaccordeReseau "{str(data["grid_connected"]).lower()}"^^xsd:boolean .')
    if data.get("latitude") is not None:
        triples.append(f":{identifier} :latitude {number(data['latitude'])} .")
    if data.get("longitude") is not None:
        triples.append(f":{identifier} :longitude {number(data['longitude'])} .")
    if data.get("owner"):
        triples.append(f":{identifier} :appartientA :{data['owner']} .")
    if data.get("zone"):
        triples.append(f":{identifier} :estSitueDans :{data['zone']} .")
    for source in data.get("sources", []):
        triples.append(f":{identifier} :possede :{source} .")
        triples.append(f":{source} :alimente :{identifier} .")
    return "\n  ".join(triples)


def create_building(identifier: str, kind: str, data: dict) -> str:
    return PREFIXES + f"""INSERT DATA {{
  :{identifier} a :{kind}, owl:NamedIndividual .
  {_building_triples(identifier, kind, data)}
}}"""


BUILDING_PROPERTIES = (
    "nom",
    "consommation",
    "surface",
    "nombreOccupants",
    "nombreEtages",
    "classeEnergetique",
    "estRaccordeReseau",
    "latitude",
    "longitude",
)


def update_building(identifier: str, kind: str, data: dict) -> str:
    deleted = " ".join(f":{prop} ?old{index} ;" for index, prop in enumerate(BUILDING_PROPERTIES))
    optional = "\n  ".join(
        f"OPTIONAL {{ :{identifier} :{prop} ?old{index} }}" for index, prop in enumerate(BUILDING_PROPERTIES)
    )
    classes = " ".join(f":{c}" for c in (*BUILDING_CLASSES, "Batiment"))
    return PREFIXES + f"""DELETE {{
  :{identifier} a ?oldClass ; {deleted} :appartientA ?oldOwner ; :estSitueDans ?oldZone ; :possede ?oldSource .
  ?oldFeed :alimente :{identifier} .
}}
INSERT {{
  :{identifier} a :{kind} .
  {_building_triples(identifier, kind, data)}
}}
WHERE {{
  VALUES ?oldClass {{ {classes} }}
  :{identifier} a ?oldClass .
  {optional}
  OPTIONAL {{ :{identifier} :appartientA ?oldOwner }}
  OPTIONAL {{ :{identifier} :estSitueDans ?oldZone }}
  OPTIONAL {{ :{identifier} :possede ?oldSource }}
  OPTIONAL {{ ?oldFeed :alimente :{identifier} }}
}}"""


def delete_building(identifier: str) -> str:
    return PREFIXES + f"""DELETE WHERE {{ :{identifier} ?p ?o }} ;
DELETE WHERE {{ ?s ?p :{identifier} }}"""
