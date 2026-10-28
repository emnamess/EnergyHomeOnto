NAMESPACE = "http://www.example.org/energyhomeonto#"

PREFIX = f"""PREFIX : <{NAMESPACE}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def territory_list() -> str:
    return PREFIX + """
SELECT ?territory ?name ?kind ?population ?postalCode ?area WHERE {
  VALUES ?class { :Ville :Quartier }
  ?territory a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL { ?territory :population ?population }
  OPTIONAL { ?territory :codePostal ?postalCode }
  OPTIONAL { ?territory :superficie ?area }
}
ORDER BY ?kind ?name
"""


def territory_detail(identifier: str) -> str:
    return PREFIX + f"""
SELECT ?name ?kind ?population ?postalCode ?area WHERE {{
  :{identifier} a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ :{identifier} :population ?population }}
  OPTIONAL {{ :{identifier} :codePostal ?postalCode }}
  OPTIONAL {{ :{identifier} :superficie ?area }}
}}
"""


def territory_infrastructure(identifier: str) -> str:
    return PREFIX + f"""
SELECT DISTINCT ?element ?name ?kind WHERE {{
  ?element :estSitueDans :{identifier} ; a ?class .
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?name)
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
}}
ORDER BY ?kind ?name
"""


def actor_list() -> str:
    return PREFIX + """
SELECT ?actor ?name ?kind ?email ?phone (COUNT(DISTINCT ?equipment) AS ?managedCount) WHERE {
  VALUES ?class { :Personne :GestionnaireReseau }
  ?actor a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL { ?actor :email ?email }
  OPTIONAL { ?actor :telephone ?phone }
  OPTIONAL { ?actor :gere ?equipment }
}
GROUP BY ?actor ?name ?kind ?email ?phone
ORDER BY ?kind ?name
"""


def actor_detail(identifier: str) -> str:
    return PREFIX + f"""
SELECT ?name ?kind ?email ?phone (COUNT(DISTINCT ?equipment) AS ?managedCount) WHERE {{
  :{identifier} a ?class ; :nom ?name .
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
  OPTIONAL {{ :{identifier} :email ?email }}
  OPTIONAL {{ :{identifier} :telephone ?phone }}
  OPTIONAL {{ :{identifier} :gere ?equipment }}
}}
GROUP BY ?name ?kind ?email ?phone
"""


def managed_equipment(identifier: str) -> str:
    return PREFIX + f"""
SELECT DISTINCT ?element ?name ?kind WHERE {{
  :{identifier} :gere ?element .
  ?element a ?class .
  OPTIONAL {{ ?element :nom ?givenName }}
  BIND(COALESCE(?givenName, STRAFTER(STR(?element), "#")) AS ?name)
  BIND(STRAFTER(STR(?class), "#") AS ?kind)
}}
ORDER BY ?kind ?name
"""
