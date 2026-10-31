"""Chiffres clés de l'ontologie et des inférences pour la page d'accueil."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.shared.rdf_store import query, store
from app.shared.sparql import NAMESPACE, PREFIXES, local_name

router = APIRouter(tags=["Tableau de bord"])

FAMILIES = (
    ("Batiment", "Bâtiments"),
    ("SourceEnergie", "Sources d’énergie"),
    ("Stockage", "Stockage"),
    ("LigneElectrique", "Lignes électriques"),
    ("EquipementReseau", "Équipements réseau"),
    ("Acteur", "Acteurs"),
    ("Zone", "Zones"),
)
AXIOM_PREDICATES = (
    "rdfs:subClassOf", "owl:equivalentClass", "owl:disjointWith", "rdfs:domain", "rdfs:range",
    "owl:inverseOf", "rdfs:subPropertyOf",
)
AXIOM_TYPES = ("owl:FunctionalProperty", "owl:TransitiveProperty", "owl:AllDisjointClasses", "owl:AllDifferent")


class Family(BaseModel):
    id: str
    label: str
    count: int


class DefinedClass(BaseModel):
    id: str
    comment: str | None
    asserted: int
    members: list[str]


class Dashboard(BaseModel):
    classes: int
    object_properties: int
    data_properties: int
    individuals: int
    axioms: int
    asserted_triples: int
    inferred_triples: int
    families: list[Family]
    defined_classes: list[DefinedClass]


def _count(sparql: str) -> int:
    return int(query(PREFIXES + sparql, inferred=False)[0]["n"])


def _named(variable: str) -> str:
    return f'FILTER(STRSTARTS(STR(?{variable}), "{NAMESPACE}"))'


@router.get("/tableau-de-bord", response_model=Dashboard)
def dashboard() -> Dashboard:
    values = " ".join(f":{family}" for family, _ in FAMILIES)
    counts = {
        local_name(row["family"]): int(row["n"])
        for row in query(PREFIXES + f"""SELECT ?family (COUNT(DISTINCT ?x) AS ?n) WHERE {{
  VALUES ?family {{ {values} }} ?x a ?family ; a owl:NamedIndividual .
}} GROUP BY ?family""")
    }

    defined: dict[str, DefinedClass] = {}
    for row in query(PREFIXES + f"""SELECT ?class ?comment (COUNT(DISTINCT ?declared) AS ?n) WHERE {{
  ?class owl:equivalentClass ?definition . {_named('class')}
  OPTIONAL {{ ?class rdfs:comment ?comment }}
  OPTIONAL {{ ?declared a ?class ; a owl:NamedIndividual }}
}} GROUP BY ?class ?comment ORDER BY ?class""", inferred=False):
        name = local_name(row["class"])
        defined[name] = DefinedClass(id=name, comment=row.get("comment"), asserted=int(row["n"]), members=[])
    for row in query(PREFIXES + f"""SELECT DISTINCT ?class ?x WHERE {{
  ?class owl:equivalentClass ?definition . {_named('class')}
  ?x a ?class ; a owl:NamedIndividual .
}} ORDER BY ?x"""):
        # Le raisonneur ajoute aussi des équivalences triviales (C ≡ C) : on ne garde que les classes définies.
        if local_name(row["class"]) in defined:
            defined[local_name(row["class"])].members.append(local_name(row["x"]))

    current = store()
    return Dashboard(
        classes=_count(f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ ?c a owl:Class . {_named('c')} }}"),
        object_properties=_count(f"SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {{ ?p a owl:ObjectProperty . {_named('p')} }}"),
        data_properties=_count(f"SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {{ ?p a owl:DatatypeProperty . {_named('p')} }}"),
        individuals=_count("SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { ?i a owl:NamedIndividual }"),
        axioms=_count(f"""SELECT (COUNT(*) AS ?n) WHERE {{
  {{ VALUES ?p {{ {' '.join(AXIOM_PREDICATES)} }} ?s ?p ?o }}
  UNION {{ VALUES ?t {{ {' '.join(AXIOM_TYPES)} }} ?s a ?t }}
}}"""),
        asserted_triples=len(current.asserted),
        inferred_triples=len(current.inferred),
        families=[Family(id=family, label=label, count=counts.get(family, 0)) for family, label in FAMILIES],
        defined_classes=sorted(defined.values(), key=lambda item: (-len(item.members), item.id)),
    )
