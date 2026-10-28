"""Requêtes SPARQL de la feature Territoires et acteurs (lecture, filtrage et CRUD)."""

from app.shared.sparql import PREFIXES, most_specific_kind, string

TERRITORY_CLASSES = ("Ville", "Quartier")
ACTOR_CLASSES = ("Personne", "GestionnaireReseau")


def _values(classes: tuple[str, ...], kind: str | None) -> str:
    selected = [kind] if kind in classes else list(classes)
    return "VALUES ?class { " + " ".join(f":{c}" for c in selected) + " }"


def _text_filter(variable: str, text: str | None) -> str:
    if not text:
        return ""
    return f"FILTER(CONTAINS(LCASE(STR(?{variable})), LCASE({string(text)})))"


def territory_list(kind: str | None = None, text: str | None = None) -> str:
    return PREFIXES + f"""
SELECT ?territory ?name ?kind ?population ?postalCode ?area WHERE {{
  {_values(TERRITORY_CLASSES, kind)}
  ?territory a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ ?territory :population ?population }}
  OPTIONAL {{ ?territory :codePostal ?postalCode }}
  OPTIONAL {{ ?territory :superficie ?area }}
  {_text_filter("name", text)}
}}
ORDER BY ?kind ?name
"""


def territory_detail(identifier: str) -> str:
    return PREFIXES + f"""
SELECT ?name ?kind ?population ?postalCode ?area WHERE {{
  {_values(TERRITORY_CLASSES, None)}
  :{identifier} a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ :{identifier} :population ?population }}
  OPTIONAL {{ :{identifier} :codePostal ?postalCode }}
  OPTIONAL {{ :{identifier} :superficie ?area }}
}}
"""


def _elements(pattern: str) -> str:
    """Éléments liés, avec leur classe la plus précise obtenue par le raisonneur."""
    return PREFIXES + f"""
SELECT ?element (SAMPLE(?label) AS ?name) (GROUP_CONCAT(DISTINCT ?kind; separator=", ") AS ?kinds) WHERE {{
  {pattern}
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?label)
  {most_specific_kind("element")}
}}
GROUP BY ?element
ORDER BY ?kinds ?name
"""


def territory_infrastructure(identifier: str) -> str:
    # estSitueDans est transitive : une ville contient aussi les éléments de ses quartiers.
    return _elements(f"?element :estSitueDans :{identifier} .")


def actor_list(kind: str | None = None, text: str | None = None) -> str:
    return PREFIXES + f"""
SELECT ?actor ?name ?kind ?email ?phone (COUNT(DISTINCT ?equipment) AS ?managedCount) WHERE {{
  {_values(ACTOR_CLASSES, kind)}
  ?actor a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ ?actor :email ?email }}
  OPTIONAL {{ ?actor :telephone ?phone }}
  OPTIONAL {{ ?actor :gere ?equipment }}
  {_text_filter("name", text)}
}}
GROUP BY ?actor ?name ?kind ?email ?phone
ORDER BY ?kind ?name
"""


def actor_detail(identifier: str) -> str:
    return PREFIXES + f"""
SELECT ?name ?kind ?email ?phone (COUNT(DISTINCT ?equipment) AS ?managedCount) WHERE {{
  {_values(ACTOR_CLASSES, None)}
  :{identifier} a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ :{identifier} :email ?email }}
  OPTIONAL {{ :{identifier} :telephone ?phone }}
  OPTIONAL {{ :{identifier} :gere ?equipment }}
}}
GROUP BY ?name ?kind ?email ?phone
"""


def managed_equipment(identifier: str) -> str:
    return _elements(f":{identifier} :gere ?element .")


def owned_buildings(identifier: str) -> str:
    # estProprietaireDe n'est pas saisi : il est déduit de appartientA (owl:inverseOf).
    return _elements(f":{identifier} :estProprietaireDe ?element .")


def actor_exists(identifier: str) -> str:
    return PREFIXES + f"ASK {{ :{identifier} ?p ?o }}"


def _actor_triples(identifier: str, name: str, email: str | None, phone: str | None) -> str:
    triples = [f":{identifier} :nom {string(name)} ."]
    if email:
        triples.append(f":{identifier} :email {string(email)} .")
    if phone:
        triples.append(f":{identifier} :telephone {string(phone)} .")
    return "\n  ".join(triples)


def create_actor(identifier: str, kind: str, name: str, email: str | None, phone: str | None) -> str:
    return PREFIXES + f"""INSERT DATA {{
  :{identifier} a :{kind}, owl:NamedIndividual .
  {_actor_triples(identifier, name, email, phone)}
}}"""


def update_actor(identifier: str, kind: str, name: str, email: str | None, phone: str | None) -> str:
    return PREFIXES + f"""DELETE {{
  :{identifier} a ?oldClass ; :nom ?oldName ; :email ?oldEmail ; :telephone ?oldPhone .
}}
INSERT {{
  :{identifier} a :{kind} .
  {_actor_triples(identifier, name, email, phone)}
}}
WHERE {{
  VALUES ?oldClass {{ {" ".join(f":{c}" for c in ACTOR_CLASSES)} }}
  :{identifier} a ?oldClass .
  OPTIONAL {{ :{identifier} :nom ?oldName }}
  OPTIONAL {{ :{identifier} :email ?oldEmail }}
  OPTIONAL {{ :{identifier} :telephone ?oldPhone }}
}}"""


def delete_actor(identifier: str) -> str:
    return PREFIXES + f"""DELETE WHERE {{ :{identifier} ?p ?o }} ;
DELETE WHERE {{ ?s ?p :{identifier} }}"""
