"""Traduction d'une question en français vers une requête SPARQL.

1. spaCy analyse la phrase (voir analyse.py) et repère les termes de l'ontologie.
2. Le premier concept (classe) devient la cible ; à défaut, un individu est décrit.
3. Chaque autre terme devient une contrainte :
   - sous-classe de la cible  -> contrainte de type (« maisons non autonomes ») ;
   - classe ou individu       -> relation choisie grâce aux domaines/portées
     de l'ontologie et au verbe de la phrase (« gérées par », « alimentés ») ;
   - propriété de données     -> filtre numérique, superlatif ou valeur affichée.
4. La négation (« sans », « pas de »...) produit un FILTER NOT EXISTS.
"""

from dataclasses import dataclass, field

from app.shared.recherche.analyse import Analyse, Mention, analyser, cle
from app.shared.recherche.vocabulaire import Vocabulaire, normalize, vocabulaire
from app.shared.sparql import PREFIXES, number, string

# Lemme d'un verbe ou d'une préposition -> propriétés qu'il évoque.
INDICES = {
    "posseder": ["possede"], "avoir": ["possede", "estEquipeDe"], "disposer": ["possede"], "detenir": ["possede"],
    "equiper": ["estEquipeDe", "possede"], "alimenter": ["estAlimentePar", "alimente"], "fournir": ["alimente"],
    "appartenir": ["appartientA"], "proprietaire": ["appartientA", "estProprietaireDe"],
    "gerer": ["estGerePar", "gere"], "exploiter": ["estGerePar", "gere"],
    "situer": ["estSitueDans"], "trouver": ["estSitueDans"], "localiser": ["estSitueDans"], "dans": ["estSitueDans"],
    "relier": ["relie"], "connecter": ["relie"], "raccorder": ["relie"],
    "stocker": ["stockeDans"], "remplir": ["stockeDans"], "recharger": ["stockeDans"], "charger": ["stockeDans"],
    "accumuler": ["stockeDans"], "installer": ["estInstalleDans"],
    "concerner": ["concerne"], "subir": ["aSubi"],
}
# Ordre de préférence quand aucun verbe ne départage plusieurs propriétés possibles.
PRIORITE = [
    "estSitueDans", "possede", "appartientA", "estAlimentePar", "alimente", "estEquipeDe", "estInstalleDans",
    "estGerePar", "gere", "stockeDans", "relie", "estProprietaireDe", "transmetEnergieA",
]


@dataclass(frozen=True)
class InterpretedQuery:
    interpretation: str
    sparql: str
    analyse: dict = field(default_factory=dict)


@dataclass
class Requete:
    motifs: list[str] = field(default_factory=list)
    colonnes: list[str] = field(default_factory=list)
    clauses: list[str] = field(default_factory=list)
    tri: str = ""


def _indices(analyse: Analyse, debut: int, mention: Mention) -> list[str]:
    doc = analyse.doc
    tokens = list(doc[debut:mention.debut]) + list(doc[mention.debut].ancestors)
    lemmes = {normalize(t.lemma_) for t in tokens} | {cle(t) for t in tokens}
    proprietes = [p for lemme in lemmes for p in INDICES.get(lemme, [])]
    proprietes += [m.terme.iri for m in analyse.mentions if m.terme.nature == "objet" and debut <= m.debut < mention.debut]
    return proprietes


def _relation(voc: Vocabulaire, source: set[str], cible: set[str], indices: list[str]) -> tuple[str, bool] | None:
    """Propriété reliant une classe source à une classe cible ; bool = sens direct (source -> cible)."""
    def convient(p: str, de: set[str], vers: set[str]) -> bool:
        domaine, portee = voc.domaines.get(p, set()), voc.portees.get(p, set())
        if not domaine and not portee and p not in indices:
            return False
        return any(voc.compatible(c, domaine) for c in de) and any(voc.compatible(c, portee) for c in vers)

    for p in dict.fromkeys(p for p in indices + PRIORITE + sorted(voc.relations) if p in voc.relations):
        if convient(p, source, cible):
            return p, True
        if convient(p, cible, source):
            return p, False
    return None


def _contrainte(motif: str, negation: bool) -> str:
    return f"FILTER NOT EXISTS {{ {motif} }}" if negation else motif


def _decrire(individu: str, voc: Vocabulaire) -> tuple[str, str]:
    sparql = PREFIXES + f"""SELECT ?propriete ?valeur WHERE {{
  {{ :{individu} ?p ?valeur . FILTER(STRSTARTS(STR(?p), STR(:))) BIND(STRAFTER(STR(?p), "#") AS ?propriete) }}
  UNION
  {{ :{individu} a ?valeur . FILTER(STRSTARTS(STR(?valeur), STR(:))) BIND("type" AS ?propriete) }}
}}
ORDER BY ?propriete ?valeur"""
    return f"Description de « {voc.noms.get(individu, individu)} » (:{individu})", sparql


def _donnee(requete: Requete, analyse: Analyse, index: int, propriete: str, sujet: str) -> None:
    valeur = f"?{propriete}"
    requete.motifs.append(f"{sujet} :{propriete} {valeur} .")
    if valeur not in requete.colonnes:
        requete.colonnes.append(valeur)
    comparaison = analyse.comparaisons.get(index)
    if comparaison and comparaison.operateur == "entre":
        requete.motifs.append(f"FILTER({valeur} >= {number(comparaison.valeur)} && {valeur} <= {number(comparaison.valeur_max)})")
        requete.clauses.append(f"{propriete} entre {comparaison.valeur:g} et {comparaison.valeur_max:g}")
    elif comparaison and isinstance(comparaison.valeur, str):
        requete.motifs.append(f"FILTER(LCASE(STR({valeur})) = LCASE({string(comparaison.valeur)}))")
        requete.clauses.append(f"{propriete} = « {comparaison.valeur} »")
    elif comparaison:
        requete.motifs.append(f"FILTER({valeur} {comparaison.operateur} {number(comparaison.valeur)})")
        requete.clauses.append(f"{propriete} {comparaison.operateur} {comparaison.valeur:g}")
    elif index in analyse.superlatifs:
        ordre = analyse.superlatifs[index]
        requete.tri = f"ORDER BY {ordre}({valeur})\nLIMIT 1"
        requete.clauses.append(f"{propriete} {'maximal' if ordre == 'DESC' else 'minimal'}")
    else:
        requete.clauses.append(f"avec {propriete}")


def interpret(question: str) -> InterpretedQuery:
    if not question or not question.strip():
        raise ValueError("Saisissez une question.")
    voc = vocabulaire()
    analyse = analyser(question, voc)
    mentions = analyse.mentions

    cible_index = next((i for i, m in enumerate(mentions) if m.terme.nature == "classe"), None)
    if cible_index is not None:
        cible = mentions[cible_index].terme.iri
    else:
        individu = next((m for m in mentions if m.terme.nature == "individu"), None)
        donnee = next((m for m in mentions if m.terme.nature == "donnee"), None)
        if individu:
            interpretation, sparql = _decrire(individu.terme.iri, voc)
            return InterpretedQuery(interpretation, sparql, analyse.resume())
        if not donnee or len(voc.domaines_donnees.get(donnee.terme.iri, set())) != 1:
            raise ValueError(
                "Aucun concept de l'ontologie reconnu. Exemples : « maisons sans panneau solaire », "
                "« batteries avec une capacité supérieure à 20 », « lignes gérées par la STEG »."
            )
        cible = next(iter(voc.domaines_donnees[donnee.terme.iri]))

    requete = Requete(motifs=[f"?x a :{cible} .", "OPTIONAL { ?x :nom ?nom }"])
    variables: list[tuple[str, str]] = [("?x", cible)]  # sujets possibles des propriétés de données
    ancre = mentions[cible_index].fin if cible_index is not None else 0

    for index, mention in enumerate(mentions):
        if index == cible_index:
            continue
        terme, negation = mention.terme, mention.negation
        prefixe = "sans " if negation else ""

        if terme.nature == "classe" and voc.sous_classe(terme.iri, cible):
            requete.motifs.append(_contrainte(f"?x a :{terme.iri} .", negation))
            requete.clauses.append(f"{prefixe}de type :{terme.iri}")
        elif terme.nature in ("classe", "individu"):
            classes = {terme.iri} if terme.nature == "classe" else voc.classes_de(terme.iri)
            relation = _relation(voc, {cible}, classes, _indices(analyse, ancre, mention))
            if relation is None:
                raise ValueError(f"Aucune propriété de l'ontologie ne relie :{cible} et « {mention.texte} ».")
            propriete, direct = relation
            objet = f"?y{index}" if terme.nature == "classe" else f":{terme.iri}"
            triple = f"?x :{propriete} {objet} ." if direct else f"{objet} :{propriete} ?x ."
            if terme.nature == "classe":
                triple += f" {objet} a :{terme.iri} ."
                if not negation:
                    variables.append((objet, terme.iri))
            requete.motifs.append(_contrainte(triple, negation))
            designation = f":{terme.iri}" if terme.nature == "classe" else f"« {mention.texte} »"
            requete.clauses.append(f"{prefixe}{'' if direct else '^'}:{propriete} {designation}")
            ancre = mention.fin
        elif terme.nature == "donnee":
            domaine = voc.domaines_donnees.get(terme.iri, set())
            sujet = next((v for v, c in reversed(variables) if voc.compatible(c, domaine)), "?x")
            _donnee(requete, analyse, index, terme.iri, sujet)

    corps = "\n".join(f"  {motif}" for motif in requete.motifs)
    if analyse.comptage:
        selection, tri = "(COUNT(DISTINCT ?x) AS ?nombre)", ""
    else:
        selection = " ".join(["?x", "?nom", *requete.colonnes])
        tri = requete.tri or "ORDER BY ?nom ?x"
    sparql = PREFIXES + f"SELECT DISTINCT {selection} WHERE {{\n{corps}\n}}" + (f"\n{tri}" if tri else "")
    debut = "Nombre d'instances" if analyse.comptage else "Instances"
    interpretation = f"{debut} de :{cible}" + (" — " + " ; ".join(requete.clauses) if requete.clauses else "")
    return InterpretedQuery(interpretation, sparql, analyse.resume())
