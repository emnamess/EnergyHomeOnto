"""Moteur local déterministe de traduction français vers SPARQL."""

from dataclasses import dataclass
import re
import unicodedata

NAMESPACE = "http://www.example.org/energyhomeonto#"


@dataclass(frozen=True)
class InterpretedQuery:
    interpretation: str
    sparql: str


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", without_accents)).strip()


def interpret(question: str) -> InterpretedQuery:
    if not question or not question.strip():
        raise ValueError("Saisissez une question.")

    text = normalize(question)
    targets = (
        (r"\b(batterie|batteries)\b", "Batterie", "batterie"),
        (r"\b(panneau|panneaux|solaire|solaires)\b", "PanneauSolaire", "panneau solaire"),
        (r"\b(eolienne|eoliennes)\b", "Eolienne", "éolienne"),
    )
    match = next((item for item in targets if re.search(item[0], text)), None)
    if match is None:
        raise ValueError("Concept non reconnu. Essayez batterie, panneau solaire ou éolienne.")

    _, target_class, label = match
    autonomous = "autonome" in text
    house_class = "MaisonAutonome" if autonomous else "Maison"
    interpretation = f"{'Maisons autonomes' if autonomous else 'Maisons'} possédant un(e) {label}"
    sparql = f"""PREFIX : <{NAMESPACE}>
SELECT DISTINCT ?maison WHERE {{
  ?maison a :{house_class} ;
          :possede ?equipement .
  ?equipement a :{target_class} .
}}"""
    return InterpretedQuery(interpretation=interpretation, sparql=sparql)
