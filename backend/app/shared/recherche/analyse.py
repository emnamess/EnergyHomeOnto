"""Analyse linguistique de la question avec spaCy (modèle fr_core_news_sm).

Étapes : tokenisation, lemmatisation, étiquetage morpho-syntaxique et analyse
en dépendances par spaCy, puis reconnaissance des termes de l'ontologie
(entités), de la négation, des comparaisons numériques et des superlatifs.
"""

from dataclasses import dataclass, field
from functools import lru_cache
import re

import spacy
from spacy.tokens import Doc, Span, Token

from app.shared.recherche.vocabulaire import LIAISONS, Terme, Vocabulaire, normalize, words

NEGATIONS = {"sans", "aucun", "aucune", "pas", "jamais", "ni", "non"}
COMPTAGE = {"combien"}
SUPERLATIF_HAUT = {"grand", "grande", "eleve", "elevee", "haut", "haute", "puissant", "puissante", "important", "gros", "fort", "forte", "maximum", "max"}
SUPERLATIF_BAS = {"petit", "petite", "faible", "bas", "basse", "minimum", "min"}
OPERATEURS = (
    (r"\bau moins\b|\bminimum\b|>=|≥|superieure?s? ou egale?s?", ">="),
    (r"\bau plus\b|\bmaximum\b|<=|≤|inferieure?s? ou egale?s?", "<="),
    (r"\bsuperieure?s?\b|\bplus de\b|\bplus que\b|\bdepass|\bau dessus\b|>", ">"),
    (r"\binferieure?s?\b|\bmoins de\b|\bmoins que\b|\ben dessous\b|<", "<"),
)


@dataclass
class Mention:
    debut: int
    fin: int
    texte: str
    terme: Terme
    negation: bool = False


@dataclass
class Comparaison:
    propriete: str
    operateur: str  # >, >=, <, <=, =, entre
    valeur: float | str
    valeur_max: float | None = None


@dataclass
class Analyse:
    doc: Doc
    mentions: list[Mention] = field(default_factory=list)
    comparaisons: dict[int, Comparaison] = field(default_factory=dict)  # index de mention -> comparaison
    superlatifs: dict[int, str] = field(default_factory=dict)  # index de mention -> DESC | ASC
    comptage: bool = False

    def resume(self) -> dict:
        return {
            "tokens": [
                {"texte": t.text, "lemme": t.lemma_, "categorie": t.pos_, "dependance": t.dep_, "tete": t.head.text}
                for t in self.doc
            ],
            "entites": [
                {"texte": m.texte, "nature": m.terme.nature, "iri": m.terme.iri, "negation": m.negation}
                for m in self.mentions
            ],
            "comptage": self.comptage,
        }


@lru_cache(maxsize=1)
def nlp() -> spacy.language.Language:
    return spacy.load("fr_core_news_sm")


def cle(token: Token) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize(token.text))


def _formes(token: Token) -> set[tuple[str, ...]]:
    return {forme for forme in (words(token.text), words(token.lemma_)) if forme}


def _reconnaitre(doc: Doc, voc: Vocabulaire) -> list[Mention]:
    """Recherche gloutonne du terme le plus long à chaque position (lemme ou forme du mot)."""
    prefixes = {cle_terme[:n] for cle_terme in voc.termes for n in range(1, len(cle_terme) + 1)}
    mentions, i = [], 0
    while i < len(doc):
        meilleur = None
        candidats: set[tuple[str, ...]] = {()}
        j = i
        while j < len(doc) and candidats:
            if j > i and cle(doc[j]) in LIAISONS:
                j += 1
                continue
            candidats = {c + f for c in candidats for f in _formes(doc[j]) if c + f in prefixes}
            trouve = next((voc.termes[c] for c in sorted(candidats, key=len, reverse=True) if c in voc.termes), None)
            if trouve:
                meilleur = (j + 1, trouve)
            j += 1
        if meilleur:
            fin, terme = meilleur
            mentions.append(Mention(i, fin, doc[i:fin].text, terme))
            i = fin
        else:
            i += 1
    return mentions


def _fusionner(mentions: list[Mention], voc: Vocabulaire) -> list[Mention]:
    """« le quartier Les Berges du Lac » : la classe qui précède un de ses individus n'est qu'un désignateur."""
    resultat: list[Mention] = []
    for mention in mentions:
        precedente = resultat[-1] if resultat else None
        if (
            precedente and precedente.terme.nature == "classe" and mention.terme.nature == "individu"
            and mention.debut - precedente.fin <= 1 and precedente.terme.iri in voc.classes_de(mention.terme.iri)
        ):
            resultat[-1] = Mention(precedente.debut, mention.fin, f"{precedente.texte} {mention.texte}", mention.terme)
        else:
            resultat.append(mention)
    return resultat


def _nombre(token: Token) -> float | None:
    texte = token.text.replace(",", ".")
    try:
        return float(texte)
    except ValueError:
        return None


def _comparer(fenetre: Span, propriete: str) -> Comparaison | None:
    nombres = [n for n in (_nombre(t) for t in fenetre) if n is not None]
    texte = " ".join(normalize(t.text) for t in fenetre)
    if len(nombres) >= 2 and re.search(r"\bentre\b", texte):
        return Comparaison(propriete, "entre", min(nombres[:2]), max(nombres[:2]))
    if nombres:
        operateur = next((op for motif, op in OPERATEURS if re.search(motif, texte)), "=")
        return Comparaison(propriete, operateur, nombres[0])
    return None


def analyser(question: str, voc: Vocabulaire) -> Analyse:
    doc = nlp()(question)
    analyse = Analyse(doc, _fusionner(_reconnaitre(doc, voc), voc))
    mentions = analyse.mentions
    analyse.comptage = any(cle(t) in COMPTAGE for t in doc) or (
        len(doc) > 1 and cle(doc[0]) == "nombre" and not (mentions and mentions[0].debut == 0)
    )

    for index, mention in enumerate(mentions):
        precedente = mentions[index - 1].fin if index else 0
        avant = doc[precedente:mention.debut]
        mention.negation = index > 0 and any(cle(t) in NEGATIONS for t in avant)

        if mention.terme.nature != "donnee":
            continue
        suivante = mentions[index + 1].debut if index + 1 < len(mentions) else len(doc)
        apres = doc[mention.fin:suivante]
        comparaison = _comparer(apres, mention.terme.iri) or _comparer(avant, mention.terme.iri)
        valeur = next((t.text for t in apres if not (t.text.islower() and cle(t) in LIAISONS)), "")
        if comparaison is None and re.fullmatch(r"[A-Z0-9][\w-]*", valeur):
            comparaison = Comparaison(mention.terme.iri, "=", valeur)
        if comparaison:
            analyse.comparaisons[index] = comparaison
            continue
        mots = {cle(t) for t in avant} | {cle(t) for t in doc[mention.debut:mention.fin]} | {cle(t) for t in apres[:3]}
        if "plus" in mots and mots & SUPERLATIF_HAUT or mots & {"maximum", "max"}:
            analyse.superlatifs[index] = "DESC"
        elif ("plus" in mots and mots & SUPERLATIF_BAS) or "moins" in mots or mots & {"minimum", "min"}:
            analyse.superlatifs[index] = "ASC"
    return analyse
