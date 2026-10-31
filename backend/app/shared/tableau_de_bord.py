"""Chiffres clés de l'ontologie, inférences et alertes du scénario pour la page d'accueil."""

import datetime

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


class AlertItem(BaseModel):
    id: str
    name: str
    detail: str
    action: str | None  # lien vers la page qui permet de traiter l'alerte


class Alert(BaseModel):
    id: str
    title: str
    rule: str  # règle de l'ontologie qui définit l'alerte, affichée pour la soutenance
    severity: str  # critique | attention | info
    items: list[AlertItem]


def _label(row: dict[str, str], variable: str) -> str:
    return row.get("nom") or local_name(row[variable])


def alerts() -> list[Alert]:
    """Diagnostic du scénario : chaque alerte est une requête sur le graphe inféré par le raisonneur."""
    year = datetime.date.today().year
    unprotected = query(PREFIXES + """SELECT ?b ?nom ?kind WHERE {
  ?b a :BatimentPublic ; a owl:NamedIndividual ; a ?k .
  VALUES ?k { :Ecole :Hopital :Mairie }
  BIND(STRAFTER(STR(?k), "#") AS ?kind)
  FILTER NOT EXISTS { ?b a :BatimentAvecStockage }
  OPTIONAL { ?b :nom ?nom }
} ORDER BY ?nom""")
    ageing = query(PREFIXES + f"""SELECT ?e ?nom ?remaining WHERE {{
  ?e a :EquipementMaintenable ; a owl:NamedIndividual ; :anneeInstallation ?annee ; :dureeVie ?duree .
  BIND(?annee + ?duree - {year} AS ?remaining)
  FILTER(?remaining <= 2)
  FILTER NOT EXISTS {{ ?e a :EquipementEntretenu }}
  OPTIONAL {{ ?e :nom ?nom }}
}} ORDER BY ?remaining""")
    energy_hungry = query(PREFIXES + """SELECT ?m ?nom ?classe ?conso WHERE {
  ?m a :Maison ; a owl:NamedIndividual ; :classeEnergetique ?classe ; :consommation ?conso .
  FILTER(STR(?classe) IN ("E", "F", "G"))
  FILTER NOT EXISTS { ?m a :MaisonAutonome }
  OPTIONAL { ?m :nom ?nom }
} ORDER BY DESC(?conso)""")

    def years(value: str) -> str:
        remaining = int(value)
        if remaining < 0:
            return f"fin de vie dépassée depuis {-remaining} an{'s' if remaining < -1 else ''}"
        return "fin de vie cette année" if remaining == 0 else f"fin de vie dans {remaining} an{'s' if remaining > 1 else ''}"

    return [
        Alert(
            id="batiments-non-secourus", severity="critique",
            title="Bâtiments publics sans stockage d’énergie",
            rule="BatimentPublic ⊓ ¬BatimentAvecStockage — BatimentAvecStockage ≡ Batiment ⊓ ∃estAlimentePar.Stockage",
            items=[AlertItem(id=local_name(r["b"]), name=_label(r, "b"), detail=r["kind"].replace("Ecole", "École").replace("Hopital", "Hôpital"),
                             action=f"#/stockage?batiment={local_name(r['b'])}") for r in unprotected],
        ),
        Alert(
            id="fin-de-vie", severity="attention",
            title="Équipements en fin de vie sans entretien préventif",
            rule="EquipementMaintenable ⊓ ¬EquipementEntretenu — EquipementEntretenu ≡ EquipementMaintenable ⊓ ∃aSubi.InterventionPreventive",
            items=[AlertItem(id=local_name(r["e"]), name=_label(r, "e"), detail=years(r["remaining"]),
                             action=f"#/maintenance?equipement={local_name(r['e'])}") for r in ageing],
        ),
        Alert(
            id="maisons-energivores", severity="info",
            title="Maisons énergivores non autonomes",
            rule="Maison ⊓ ¬MaisonAutonome, classe énergétique E à G — à transmettre à l’équipe Production (feature à venir)",
            items=[AlertItem(id=local_name(r["m"]), name=_label(r, "m"), detail=f"classe {r['classe']} · {float(r['conso']):g} kWh", action=None)
                   for r in energy_hungry],
        ),
    ]


@router.get("/tableau-de-bord/alertes", response_model=list[Alert])
def dashboard_alerts() -> list[Alert]:
    return alerts()


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
