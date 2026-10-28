"""Moteur local déterministe de traduction français vers SPARQL."""

from dataclasses import dataclass
import re
import unicodedata

NAMESPACE = "http://www.example.org/energyhomeonto#"

# (motif, classe OWL, article, libellé)
EQUIPMENTS = (
    (r"batteries?", "Batterie", "une", "batterie"),
    (r"panneaux?(?: solaires?)?|solaires?", "PanneauSolaire", "un", "panneau solaire"),
    (r"eoliennes?", "Eolienne", "une", "éolienne"),
)
NEGATION = r"(?:sans|aucune?|pas|non|ni)(?: (?:de|d|du|un|une|des|la|le|l))?"
UNSUPPORTED = (
    "Question non reconnue. La recherche porte sur les maisons (autonomes ou non) "
    "avec ou sans batterie, panneau solaire ou éolienne."
)


@dataclass(frozen=True)
class InterpretedQuery:
    interpretation: str
    sparql: str


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", without_accents)).strip()


def _polarity(pattern: str, text: str) -> bool | None:
    """True si le concept est demandé, False s'il est nié, None s'il est absent."""
    match = re.search(rf"\b(?:(?P<negation>{NEGATION}) )?(?:{pattern})\b", text)
    if match is None:
        return None
    return match.group("negation") is None


def interpret(question: str) -> InterpretedQuery:
    if not question or not question.strip():
        raise ValueError("Saisissez une question.")

    text = normalize(question)
    autonomous = _polarity(r"autonomes?", text)
    conditions = [(item, wanted) for item in EQUIPMENTS if (wanted := _polarity(item[0], text)) is not None]
    if not conditions and autonomous is None and not re.search(r"\b(maison|maisons|logements?)\b", text):
        raise ValueError(UNSUPPORTED)

    patterns = ["?maison a/rdfs:subClassOf* :Maison .", "OPTIONAL { ?maison :nom ?nom }"]
    subject = "Maisons"
    if autonomous is True:
        patterns.append("?maison a/rdfs:subClassOf* :MaisonAutonome .")
        subject += " autonomes"
    elif autonomous is False:
        patterns.append("FILTER NOT EXISTS { ?maison a/rdfs:subClassOf* :MaisonAutonome }")
        subject += " non autonomes"

    clauses = []
    for index, ((_, target_class, article, label), wanted) in enumerate(conditions):
        triple = f"?maison :possede ?equipement{index} . ?equipement{index} a/rdfs:subClassOf* :{target_class} ."
        if wanted:
            patterns.append(triple)
            clauses.append(f"avec {article} {label}")
        else:
            patterns.append(f"FILTER NOT EXISTS {{ {triple} }}")
            clauses.append(f"sans {label}")

    interpretation = " ".join([subject, " et ".join(clauses)]).strip()
    body = "\n".join(f"  {pattern}" for pattern in patterns)
    sparql = f"""PREFIX : <{NAMESPACE}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?maison ?nom WHERE {{
{body}
}}
ORDER BY ?nom"""
    return InterpretedQuery(interpretation=interpretation, sparql=sparql)
