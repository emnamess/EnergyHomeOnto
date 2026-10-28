"""Outils communs pour écrire des requêtes SPARQL sûres."""

import re

from rdflib import Literal
from rdflib.namespace import XSD

NAMESPACE = "http://www.example.org/energyhomeonto#"

PREFIXES = f"""PREFIX : <{NAMESPACE}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def local_name(uri: str) -> str:
    return uri.rsplit("#", 1)[-1]


def is_identifier(value: str) -> bool:
    return IDENTIFIER.fullmatch(value) is not None


def string(value: str) -> str:
    """Littéral chaîne échappé, utilisable sans risque d'injection."""
    return Literal(value, datatype=XSD.string).n3()


def number(value: float) -> str:
    return Literal(float(value), datatype=XSD.double).n3()


def most_specific_kind(variable: str) -> str:
    """Motif qui lie ?kind à la classe la plus précise (inférences comprises) de la variable."""
    return f"""?{variable} a ?kindClass .
  FILTER(STRSTARTS(STR(?kindClass), "{NAMESPACE}"))
  FILTER NOT EXISTS {{
    ?{variable} a ?narrower .
    ?narrower rdfs:subClassOf ?kindClass .
    FILTER(?narrower != ?kindClass && STRSTARTS(STR(?narrower), "{NAMESPACE}"))
  }}
  BIND(STRAFTER(STR(?kindClass), "#") AS ?kind)"""
