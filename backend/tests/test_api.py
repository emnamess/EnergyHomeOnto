import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.rdf_store import RdfStore
from app.shared.sparql import local_name

client = TestClient(app)
API = "/api/territoires-acteurs"


def ids(results: list[dict[str, str]], key: str = "x") -> list[str]:
    return sorted(local_name(row[key]) for row in results)


def search(question: str):
    return client.post("/api/search", json={"query": question})


def test_health_reports_inferred_triples():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["triplets_inferes"] > body["triplets_asserts"] > 1000


# --- Territoires et acteurs : lecture et filtrage ---------------------------------

def test_territories_list_and_filters():
    assert {t["id"] for t in client.get(f"{API}/territoires").json()} == {"villeTunis", "quartierLac", "quartierCentre"}
    assert [t["id"] for t in client.get(f"{API}/territoires", params={"kind": "Ville"}).json()] == ["villeTunis"]
    assert [t["id"] for t in client.get(f"{API}/territoires", params={"q": "lac"}).json()] == ["quartierLac"]


def test_territory_infrastructure_uses_reasoning():
    body = client.get(f"{API}/territoires/quartierLac").json()
    kinds = {item["id"]: item["kind"] for item in body["infrastructure"]}
    # Maison1 est déclarée :Maison ; le raisonneur la classe MaisonAutonome (possède un panneau solaire).
    assert "MaisonAutonome" in kinds["Maison1"]
    # estSitueDans est transitive : la ville contient les éléments de ses quartiers.
    tunis = {item["id"] for item in client.get(f"{API}/territoires/villeTunis").json()["infrastructure"]}
    assert {"Maison1", "hopital1", "quartierLac"} <= tunis


def test_actor_detail_with_inverse_properties():
    steg = client.get(f"{API}/acteurs/STEG").json()
    assert steg["managed_count"] == 11
    sarra = client.get(f"{API}/acteurs/sarra").json()
    # estProprietaireDe est déduit de appartientA par owl:inverseOf.
    assert {b["id"] for b in sarra["owned_buildings"]} == {"Maison2", "Maison5"}


def test_actor_filters():
    people = client.get(f"{API}/acteurs", params={"kind": "Personne"}).json()
    assert {a["id"] for a in people} == {"ahmed", "sarra", "karim"}
    assert [a["id"] for a in client.get(f"{API}/acteurs", params={"q": "trab"}).json()] == ["sarra"]


def test_concurrent_requests_do_not_break_sparql_parser():
    # Le frontend charge territoires et acteurs en parallèle : le parseur SPARQL doit le supporter.
    from concurrent.futures import ThreadPoolExecutor

    urls = [f"{API}/territoires", f"{API}/acteurs"] * 20
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda url: client.get(url).status_code, urls))
    assert set(codes) == {200}
    assert client.get(f"{API}/acteurs").status_code == 200


@pytest.mark.parametrize(
    "url",
    [
        f"{API}/territoires/inconnu",
        f"{API}/territoires/ahmed",
        f"{API}/acteurs/Maison3",
        f"{API}/acteurs/a%20b",
    ],
)
def test_detail_rejects_unknown_or_wrong_type(url):
    assert client.get(url).status_code == 404


# --- CRUD (SPARQL Update) ----------------------------------------------------------

def test_actor_crud_and_journal_replay():
    created = client.post(f"{API}/acteurs", json={"name": "Amine Mansour", "kind": "Personne", "email": "amine@example.tn"})
    assert created.status_code == 201
    identifier = created.json()["id"]
    assert "INSERT DATA" in created.json()["sparql"]
    assert client.get(f"{API}/acteurs/{identifier}").json()["email"] == "amine@example.tn"

    updated = client.put(f"{API}/acteurs/{identifier}", json={"name": "Amine Mansouri", "kind": "Personne", "phone": "+216 20 000 009"})
    assert updated.status_code == 200
    detail = client.get(f"{API}/acteurs/{identifier}").json()
    assert (detail["name"], detail["email"], detail["phone"]) == ("Amine Mansouri", None, "+216 20 000 009")

    # Le nouvel individu est aussitôt reconnu par la recherche en langage naturel.
    assert search("Amine Mansouri").json()["interpretation"].startswith("Description")

    # Le journal est rejoué au démarrage : un nouveau store retrouve la modification.
    assert RdfStore().query(f"PREFIX : <http://www.example.org/energyhomeonto#> SELECT ?n WHERE {{ :{identifier} :nom ?n }}") == [{"n": "Amine Mansouri"}]

    assert client.delete(f"{API}/acteurs/{identifier}").status_code == 200
    assert client.get(f"{API}/acteurs/{identifier}").status_code == 404
    assert client.delete(f"{API}/acteurs/{identifier}").status_code == 404


def test_actor_input_is_escaped():
    created = client.post(f"{API}/acteurs", json={"name": 'Injection" } ; DROP ALL ; #', "kind": "GestionnaireReseau"})
    identifier = created.json()["id"]
    assert client.get(f"{API}/acteurs/{identifier}").json()["name"] == 'Injection" } ; DROP ALL ; #'
    assert client.get(f"{API}/acteurs/STEG").status_code == 200
    client.delete(f"{API}/acteurs/{identifier}")


def test_actor_input_validation():
    assert client.post(f"{API}/acteurs", json={"name": "", "kind": "Personne"}).status_code == 422
    assert client.post(f"{API}/acteurs", json={"name": "X", "kind": "Maison"}).status_code == 422


# --- Recherche en langage naturel (spaCy -> SPARQL) --------------------------------

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Liste les maisons autonomes qui possèdent un panneau solaire", ["Maison1", "Maison2", "Maison5"]),
        ("maisons sans panneau solaire", ["Maison3", "Maison4"]),
        ("maisons non autonomes", ["Maison3", "Maison4"]),
        ("maisons intelligentes", ["Maison1", "Maison2", "Maison5"]),
        ("maisons avec une batterie", ["Maison5"]),
        ("maisons de Sarra", ["Maison2", "Maison5"]),
        ("lignes gérées par la STEG", ["ligneBT1", "ligneHT1", "ligneHT2", "ligneMT1", "ligneMT2"]),
        ("bâtiments alimentés par une éolienne", ["Maison3", "Maison4", "ecole1", "supermarche1"]),
        ("éoliennes du quartier Les Berges du Lac", ["eolienne1"]),
        ("Dans quel quartier se trouve la maison 1 ?", ["quartierLac"]),
        ("Quelles sont les batteries ayant une capacité supérieure à 20 ?", ["batterie1", "batterie3"]),
        ("sources d'énergie avec une puissance entre 5 et 50,5 kW", ["eolienne1", "panneausolaire1", "panneausolaire3", "panneausolaire4"]),
        ("bâtiments avec une consommation inférieure à 12", ["Maison2", "Maison4", "Maison5"]),
        ("bâtiments de classe énergétique A", ["Maison1", "Maison5"]),
        ("la batterie avec la plus grande capacité", ["batterie3"]),
        ("quel est le panneau solaire le plus puissant", ["panneausolaire4"]),
        ("lignes souterraines", ["ligne2", "ligneBT1", "ligneMT1", "ligneMT2"]),
    ],
)
def test_search(question, expected):
    response = search(question)
    assert response.status_code == 200, response.json()
    assert ids(response.json()["results"]) == expected


def test_search_counts():
    assert search("Combien de maisons à Tunis ?").json()["results"] == [{"nombre": "5"}]


def test_search_describes_individual():
    results = search("Ahmed").json()["results"]
    assert {"propriete": "estProprietaireDe", "valeur": "http://www.example.org/energyhomeonto#Maison1"} in results


def test_search_returns_spacy_analysis():
    analyse = search("maisons qui n'ont pas d'éolienne").json()["analyse"]
    assert {"texte": "ont", "lemme": "avoir"}.items() <= analyse["tokens"][3].items()
    assert analyse["entites"][-1] == {"texte": "éolienne", "nature": "classe", "iri": "Eolienne", "negation": True}


def test_search_rejects_unsupported_question():
    assert search("quelle est la météo").status_code == 400


# --- Tableau de bord ---------------------------------------------------------------

def test_dashboard_counts_and_deductions():
    body = client.get("/api/tableau-de-bord").json()
    assert (body["classes"], body["object_properties"], body["data_properties"]) == (45, 13, 43)
    assert body["inferred_triples"] > body["asserted_triples"]
    families = {family["id"]: family["count"] for family in body["families"]}
    assert families["Batiment"] == 10 and families["Zone"] == 3
    deduced = {item["id"]: item["members"] for item in body["defined_classes"]}
    assert deduced["MaisonAutonome"] == ["Maison1", "Maison2", "Maison5"]
    # Classes à seuil numérique, calculées en complément d'OWL RL.
    assert deduced["GrosConsommateur"] == ["hopital1", "supermarche1", "usine1"]
    assert deduced["SourceForte"] == ["centraleGaz1", "centraleHydro1"]
