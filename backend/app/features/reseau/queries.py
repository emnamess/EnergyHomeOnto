"""Requêtes SPARQL du réseau électrique, construites sur l'ontologie OWL."""

from app.shared.sparql import NAMESPACE, PREFIXES, number, string

LINE_CLASSES = ("LigneElectrique", "LigneHauteTension", "LigneMoyenneTension", "LigneBasseTension", "LigneSouterraine")
EQUIPMENT_CLASSES = ("PosteTransformation", "CompteurIntelligent")
NETWORK_CLASSES = (*LINE_CLASSES, *EQUIPMENT_CLASSES)
RELATED_CLASSES = (*NETWORK_CLASSES, "Batiment", "SourceEnergie", "Stockage")


def kind_within(variable: str, root: str) -> str:
    return f"""?{variable} a ?kindClass .
  ?kindClass rdfs:subClassOf :{root} .
  FILTER(STRSTARTS(STR(?kindClass), "{NAMESPACE}"))
  FILTER NOT EXISTS {{
    ?{variable} a ?narrower .
    ?narrower rdfs:subClassOf ?kindClass, :{root} .
    FILTER(?narrower != ?kindClass && STRSTARTS(STR(?narrower), "{NAMESPACE}"))
  }}
  BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)"""


def _types(kind: str | None) -> str:
    selected = (kind,) if kind in NETWORK_CLASSES else NETWORK_CLASSES
    return "VALUES ?class { " + " ".join(f":{item}" for item in selected) + " }"


def _elements(pattern: str, extra: str = "") -> str:
    return PREFIXES + f"""
SELECT ?element ?name (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds)
       ?length ?voltage ?section ?lossRate ?underground ?transformationPower ?meterIdentifier
       ?readingFrequency ?year ?lifetime ?installationCost (COUNT(DISTINCT ?related) AS ?relatedCount) WHERE {{
  {pattern}
  ?element a ?class .
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?name)
  OPTIONAL {{ ?element :longueur ?length }}
  OPTIONAL {{ ?element :tension ?voltage }}
  OPTIONAL {{ ?element :section ?section }}
  OPTIONAL {{ ?element :tauxPertes ?lossRate }}
  OPTIONAL {{ ?element :estSouterraine ?underground }}
  OPTIONAL {{ ?element :puissanceTransformation ?transformationPower }}
  OPTIONAL {{ ?element :identifiantCompteur ?meterIdentifier }}
  OPTIONAL {{ ?element :frequenceReleve ?readingFrequency }}
  OPTIONAL {{ ?element :anneeInstallation ?year }}
  OPTIONAL {{ ?element :dureeVie ?lifetime }}
  OPTIONAL {{ ?element :coutInstallation ?installationCost }}
  OPTIONAL {{ ?element :relie ?related }}
  OPTIONAL {{ ?element :estGerePar ?manager }}
  OPTIONAL {{ ?manager :gere ?related }}
  {{ {kind_within("element", "LigneElectrique")} }} UNION {{
    ?element a ?kindClass . ?kindClass rdfs:subClassOf :EquipementReseau .
    FILTER(STRSTARTS(STR(?kindClass), "{NAMESPACE}"))
    FILTER NOT EXISTS {{ ?element a ?narrower . ?narrower rdfs:subClassOf ?kindClass, :EquipementReseau . FILTER(?narrower != ?kindClass) }}
    BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)
  }}
  {extra}
}}
GROUP BY ?element ?name ?length ?voltage ?section ?lossRate ?underground ?transformationPower ?meterIdentifier ?readingFrequency ?year ?lifetime ?installationCost
ORDER BY ?name
"""


def element_list(kind: str | None = None, text: str | None = None, min_voltage: float | None = None,
                 max_voltage: float | None = None, underground: bool | None = None) -> str:
    filters = ""
    if text:
        filters += f"\n  FILTER(CONTAINS(LCASE(STR(?name)), LCASE({string(text)})))"
    if min_voltage is not None:
        filters += f"\n  FILTER(?voltage >= {number(min_voltage)})"
    if max_voltage is not None:
        filters += f"\n  FILTER(?voltage <= {number(max_voltage)})"
    if underground is not None:
        filters += f"\n  FILTER(BOUND(?underground) && ?underground = {str(underground).lower()})"
    return _elements(_types(kind) + "\n  ?element a ?class .", filters)


def element_detail(identifier: str) -> str:
    return _elements(f"VALUES ?element {{ :{identifier} }}\n  ?element a ?class .")


def inferred_classes(identifier: str) -> str:
    return PREFIXES + f"""SELECT DISTINCT ?class WHERE {{
  :{identifier} a ?class . FILTER(STRSTARTS(STR(?class), "{NAMESPACE}"))
}} ORDER BY ?class"""


def relationships(identifier: str) -> str:
    # `relie` est défini de LigneElectrique vers une ressource, sans portée restrictive.
    # Les gestionnaires sont traversés via les propriétés inverses déclarées en OWL.
    return PREFIXES + f"""SELECT DISTINCT ?element ?name ?kind WHERE {{
  {{ :{identifier} :relie ?element }} UNION {{ ?element :relie :{identifier} }}
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?name)
  ?element a ?class . FILTER(STRSTARTS(STR(?class), "{NAMESPACE}"))
  FILTER NOT EXISTS {{ ?element a ?narrower . ?narrower rdfs:subClassOf ?class . FILTER(?narrower != ?class && STRSTARTS(STR(?narrower), "{NAMESPACE}")) }}
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
}} ORDER BY ?kind ?name"""


def managers(identifier: str) -> str:
    return PREFIXES + f"""SELECT DISTINCT ?element ?name ?kind WHERE {{
  {{ :{identifier} :estGerePar ?element }} UNION {{ ?element :gere :{identifier} }}
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?name)
  ?element a ?class . FILTER(STRSTARTS(STR(?class), "{NAMESPACE}"))
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
}} ORDER BY ?name"""


def indicators() -> str:
    return PREFIXES + f"""SELECT ?kind (COUNT(DISTINCT ?element) AS ?count) WHERE {{
  {{
    {_types(None)} ?element a ?class .
    {kind_within("element", "LigneElectrique")}
  }} UNION {{
    ?element a ?kindClass . ?kindClass rdfs:subClassOf :EquipementReseau .
    FILTER(STRSTARTS(STR(?kindClass), "{NAMESPACE}"))
    FILTER NOT EXISTS {{ ?element a ?narrower . ?narrower rdfs:subClassOf ?kindClass, :EquipementReseau . FILTER(?narrower != ?kindClass) }}
    BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)
  }}
}} GROUP BY ?kind ORDER BY ?kind"""


def total_count() -> str:
    """Nombre d'individus réseau distincts, sans recompter leurs classes inférées."""
    return PREFIXES + f"""SELECT (COUNT(DISTINCT ?element) AS ?count) WHERE {{
  {_types(None)}
  ?element a ?class .
}}"""


def options(class_name: str) -> str:
    return PREFIXES + f"""SELECT ?element (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds) WHERE {{
  ?element a :{class_name} . OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?label)
  ?element a ?kindClass . FILTER(STRSTARTS(STR(?kindClass), "{NAMESPACE}"))
  FILTER NOT EXISTS {{ ?element a ?narrower . ?narrower rdfs:subClassOf ?kindClass . FILTER(?narrower != ?kindClass && STRSTARTS(STR(?narrower), "{NAMESPACE}")) }}
  BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)
}} GROUP BY ?element ORDER BY ?name"""


def is_kind(identifier: str, kind: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} a :{kind} }}"


def exists(identifier: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} ?p ?o }}"


def has_interventions(identifier: str) -> str:
    """Évite de supprimer un équipement réseau encore référencé par une intervention."""
    return PREFIXES + f"ASK {{ ?intervention :concerne :{identifier} }}"


LINE_PROPERTIES = ("nom", "longueur", "tension", "section", "tauxPertes", "estSouterraine", "anneeInstallation", "dureeVie", "coutInstallation")
EQUIPMENT_PROPERTIES = ("nom", "tension", "puissanceTransformation", "identifiantCompteur", "frequenceReleve", "dateDerniereReleve", "anneeInstallation", "dureeVie", "coutInstallation")


def _triples(identifier: str, kind: str, data: dict) -> str:
    props = LINE_PROPERTIES if kind in LINE_CLASSES else EQUIPMENT_PROPERTIES
    values = {
        "nom": string(data["name"]), "longueur": number(data["length"]) if data.get("length") is not None else None,
        "tension": number(data["voltage"]) if data.get("voltage") is not None else None,
        "section": number(data["section"]) if data.get("section") is not None else None,
        "tauxPertes": number(data["loss_rate"]) if data.get("loss_rate") is not None else None,
        "estSouterraine": str(data["underground"]).lower() if data.get("underground") is not None else None,
        "puissanceTransformation": number(data["transformation_power"]) if data.get("transformation_power") is not None else None,
        "identifiantCompteur": string(data["meter_identifier"]) if data.get("meter_identifier") else None,
        "frequenceReleve": f'"{int(data["reading_frequency"])}"^^xsd:integer' if data.get("reading_frequency") is not None else None,
        "anneeInstallation": f'"{int(data["installation_year"])}"^^xsd:integer' if data.get("installation_year") is not None else None,
        "dureeVie": f'"{int(data["lifetime_years"])}"^^xsd:integer' if data.get("lifetime_years") is not None else None,
        "coutInstallation": number(data["installation_cost"]) if data.get("installation_cost") is not None else None,
    }
    triples = [f":{identifier} :{prop} {values[prop]} ." for prop in props if values.get(prop) is not None]
    triples.extend(f":{identifier} :relie :{related} ." for related in data.get("related", []))
    triples.extend(f":{manager} :gere :{identifier} ." for manager in data.get("managers", []))
    return "\n  ".join(triples)


def create_element(identifier: str, kind: str, data: dict) -> str:
    return PREFIXES + f"""INSERT DATA {{
  :{identifier} a :{kind}, owl:NamedIndividual .
  {_triples(identifier, kind, data)}
}}"""


def update_element(identifier: str, kind: str, data: dict) -> str:
    allowed = " ".join(f":{item}" for item in NETWORK_CLASSES)
    properties = tuple(dict.fromkeys((*LINE_PROPERTIES, *EQUIPMENT_PROPERTIES)))
    old_props = " ".join(f"; :{prop} ?old{index}" for index, prop in enumerate(properties))
    optional = "\n  ".join(f"OPTIONAL {{ :{identifier} :{prop} ?old{index} }}" for index, prop in enumerate(properties))
    return PREFIXES + f"""DELETE {{
  :{identifier} a ?oldClass {old_props} .
  :{identifier} :relie ?oldRelated .
  ?oldManager :gere :{identifier} .
}}
INSERT {{
  :{identifier} a :{kind} .
  {_triples(identifier, kind, data)}
}}
WHERE {{
  VALUES ?oldClass {{ {allowed} }} :{identifier} a ?oldClass .
  {optional}
  OPTIONAL {{ :{identifier} :relie ?oldRelated }}
  OPTIONAL {{ ?oldManager :gere :{identifier} }}
}}"""


def delete_element(identifier: str) -> str:
    return PREFIXES + f"""DELETE WHERE {{ :{identifier} ?p ?o }} ;
DELETE WHERE {{ ?s ?p :{identifier} }}"""
