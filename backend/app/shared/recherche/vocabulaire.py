"""Lexique construit automatiquement depuis l'ontologie.

Chaque classe, propriété et individu reçoit une ou plusieurs formes
(« PanneauSolaire » -> « panneau solaire », nom de l'individu...). La structure
de l'ontologie (sous-classes, domaines et portées, propriétés inverses) sert
ensuite à choisir la propriété qui relie deux concepts d'une question.
"""

from dataclasses import dataclass, field
from functools import lru_cache
import re
import unicodedata

from app.shared.rdf_store import query, store
from app.shared.sparql import NAMESPACE, PREFIXES, local_name

# Mots ignorés à l'intérieur d'un terme : « poste de transformation », « batterie au lithium ».
LIAISONS = {"de", "d", "du", "des", "la", "le", "l", "au", "aux", "a", "en"}

# Formes supplémentaires que le découpage des identifiants ne produit pas.
SYNONYMES = {
    "Maison": ["logement", "habitation"],
    "MaisonAutonome": ["autonome"],
    "MaisonIntelligente": ["intelligente"],
    "Batiment": ["edifice"],
    "BatimentIndustriel": ["usine"],
    "BatimentCommercial": ["commerce", "supermarche"],
    "PanneauSolaire": ["panneau", "panneau photovoltaique", "photovoltaique"],
    "SourceEnergie": ["source", "producteur"],
    "LigneElectrique": ["ligne", "cable"],
    "LigneSouterraine": ["souterraine", "enterree"],
    "PosteTransformation": ["poste", "transformateur"],
    "CompteurIntelligent": ["compteur"],
    "GestionnaireReseau": ["gestionnaire", "operateur"],
    "StockageHydrogene": ["hydrogene"],
    "Acteur": ["intervenant"],
    "nombreEtages": ["etage"],
    "nombreOccupants": ["occupant", "habitant"],
    "coutInstallation": ["cout", "prix"],
    "anneeInstallation": ["annee"],
    "emissionCO2": ["emission", "co2", "emission co2"],
    "productionAnnuelle": ["production"],
    "debitEau": ["debit"],
    "hauteurMat": ["hauteur"],
    "diametreRotor": ["diametre"],
    "niveauCharge": ["charge"],
    "puissance": ["puissant"],
    "EquipementReseau": ["equipement"],
}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def singular(word: str) -> str:
    return word[:-1] if len(word) > 3 and word[-1] in "sx" else word


def words(text: str) -> tuple[str, ...]:
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Za-z])", " ", text)
    return tuple(singular(word) for word in re.findall(r"[a-z0-9]+", normalize(spaced)) if word not in LIAISONS)


@dataclass
class Terme:
    iri: str
    nature: str  # classe | objet | donnee | individu
    libelle: str


@dataclass
class Vocabulaire:
    termes: dict[tuple[str, ...], Terme] = field(default_factory=dict)
    superclasses: dict[str, set[str]] = field(default_factory=dict)
    relations: set[str] = field(default_factory=set)  # propriétés d'objet
    domaines: dict[str, set[str]] = field(default_factory=dict)
    portees: dict[str, set[str]] = field(default_factory=dict)
    domaines_donnees: dict[str, set[str]] = field(default_factory=dict)
    types: dict[str, set[str]] = field(default_factory=dict)
    noms: dict[str, str] = field(default_factory=dict)

    def ajouter(self, forme: str, terme: Terme) -> None:
        cle = words(forme)
        if cle and cle not in self.termes:
            self.termes[cle] = terme

    def sous_classe(self, classe: str, autre: str) -> bool:
        return classe == autre or autre in self.superclasses.get(classe, set())

    def compatible(self, classe: str, contraintes: set[str]) -> bool:
        """Vrai si la classe est compatible avec un domaine ou une portée (vide = sans contrainte)."""
        return not contraintes or any(self.sous_classe(classe, c) or self.sous_classe(c, classe) for c in contraintes)

    def classes_de(self, iri: str) -> set[str]:
        return self.types.get(iri, set())


def _union(rows: list[dict[str, str]], key: str, value: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for row in rows:
        result.setdefault(local_name(row[key]), set()).add(local_name(row[value]))
    return result


def _named(variable: str) -> str:
    return f'FILTER(STRSTARTS(STR(?{variable}), "{NAMESPACE}"))'


def vocabulaire() -> Vocabulaire:
    """Lexique à jour : reconstruit après chaque modification CRUD du graphe."""
    return _construire(store().version)


@lru_cache(maxsize=1)
def _construire(version: int) -> Vocabulaire:
    voc = Vocabulaire()
    classes = query(PREFIXES + f"SELECT ?c WHERE {{ ?c a owl:Class . {_named('c')} }}", inferred=False)
    objets = query(PREFIXES + f"SELECT ?p WHERE {{ ?p a owl:ObjectProperty . {_named('p')} }}", inferred=False)
    donnees = query(PREFIXES + f"SELECT ?p WHERE {{ ?p a owl:DatatypeProperty . {_named('p')} }}", inferred=False)
    voc.superclasses = _union(query(PREFIXES + f"""SELECT ?c ?s WHERE {{
  ?c rdfs:subClassOf ?s . {_named('c')} {_named('s')} FILTER(?c != ?s) }}"""), "c", "s")

    # Domaine et portée : classe nommée ou union de classes (owl:unionOf).
    def axe(type_propriete: str, axe: str) -> dict[str, set[str]]:
        return _union(query(PREFIXES + f"""SELECT ?p ?c WHERE {{
  ?p a {type_propriete} . {_named('p')}
  {{ ?p rdfs:{axe} ?c }} UNION {{ ?p rdfs:{axe}/owl:unionOf/rdf:rest*/rdf:first ?c }}
  {_named('c')} }}""", inferred=False), "p", "c")

    voc.relations = {local_name(row["p"]) for row in objets}
    voc.domaines = {p: set() for p in voc.relations} | axe("owl:ObjectProperty", "domain")
    voc.portees = {p: set() for p in voc.relations} | axe("owl:ObjectProperty", "range")
    voc.domaines_donnees = axe("owl:DatatypeProperty", "domain")
    # Une propriété inverse échange domaine et portée (gere -> estGerePar).
    for row in query(PREFIXES + "SELECT ?p ?q WHERE { ?p owl:inverseOf ?q }", inferred=False):
        p, q = local_name(row["p"]), local_name(row["q"])
        for a, b in ((p, q), (q, p)):
            voc.domaines.setdefault(a, set()).update(voc.portees.get(b, set()))
            voc.portees.setdefault(a, set()).update(voc.domaines.get(b, set()))

    individus = query(PREFIXES + f"""SELECT ?i ?c ?nom WHERE {{
  ?i a owl:NamedIndividual ; a ?c . {_named('c')}
  OPTIONAL {{ ?i :nom ?nom }} }}""")
    voc.types = _union(individus, "i", "c")
    for row in individus:
        voc.noms.setdefault(local_name(row["i"]), row.get("nom", local_name(row["i"])))

    for nature, rows, cle in (("classe", classes, "c"), ("objet", objets, "p"), ("donnee", donnees, "p")):
        for row in rows:
            nom = local_name(row[cle])
            voc.ajouter(nom, Terme(nom, nature, nom))
    for nom, formes in SYNONYMES.items():
        terme = next((t for t in voc.termes.values() if t.iri == nom), None)
        for forme in formes if terme else ():
            voc.ajouter(forme, terme)
    for individu, nom in voc.noms.items():
        terme = Terme(individu, "individu", nom)
        voc.ajouter(nom, terme)
        voc.ajouter(individu, terme)
        # « quartierLac » -> « lac », « villeTunis » -> « tunis »
        suffixe = re.sub(r"^[a-z]+(?=[A-Z])", "", individu)
        if suffixe != individu:
            voc.ajouter(suffixe, terme)
    return voc
