import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.sparql import local_name

client = TestClient(app)


def search(question: str):
    return client.post("/api/search", json={"query": question})


def ids(response) -> list[str]:
    return sorted(local_name(row["x"]) for row in response.json()["results"] if "x" in row)


@pytest.mark.parametrize(
    ("question", "concept", "kind", "sparql_type", "expected"),
    [
        ("Liste les lignes électriques", "LigneElectrique", "classe", ":LigneElectrique", [
            "ligne1", "ligne2", "ligne3", "ligneBT1", "ligneBT2", "ligneBT3", "ligneBT4",
            "ligneHT1", "ligneHT2", "ligneHT3", "ligneHT4", "ligneMT1", "ligneMT2", "ligneMT3", "ligneMT4",
        ]),
        ("Quels sont les postes de transformation ?", "PosteTransformation", "classe", ":PosteTransformation",
         ["poste1", "poste2", "poste3", "poste4", "poste5"]),
        ("Quelles lignes sont souterraines ?", "LigneElectrique", "classe", "?x :estSouterraine true",
         ["ligne2", "ligneBT1", "ligneBT2", "ligneMT1", "ligneMT2", "ligneMT3", "ligneMT4"]),
        ("Quels équipements appartiennent au réseau ?", "EquipementReseau", "classe", ":EquipementReseau",
         ["compteur1", "compteur10", "compteur11", "compteur2", "compteur3", "compteur4", "compteur5",
          "compteur6", "compteur7", "compteur8", "compteur9", "poste1", "poste2", "poste3", "poste4", "poste5"]),
    ],
)
def test_search_network_classes(question, concept, kind, sparql_type, expected):
    response = search(question)
    assert response.status_code == 200, response.json()
    body = response.json()
    assert any(item["iri"] == concept and item["nature"] == kind for item in body["analyse"]["entites"])
    assert (sparql_type in body["sparql"] if sparql_type.startswith("?") else f"a {sparql_type}" in body["sparql"])
    assert ids(response) == expected


def test_search_network_voltage_numeric_comparison():
    response = search("Quelles lignes ont une tension supérieure à 20 ?")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert any(item["iri"] == "LigneElectrique" for item in body["analyse"]["entites"])
    assert any(item["iri"] == "tension" for item in body["analyse"]["entites"])
    assert ":tension ?tension" in body["sparql"]
    assert "FILTER(?tension > \"20.0\"^^<http://www.w3.org/2001/XMLSchema#double>)" in body["sparql"]
    assert ids(response) == ["ligneHT1", "ligneHT2", "ligneHT3", "ligneHT4", "ligneMT1", "ligneMT3"]


def test_search_network_count():
    response = search("Combien de lignes électriques existent ?")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert any(item["iri"] == "LigneElectrique" for item in body["analyse"]["entites"])
    assert body["analyse"]["comptage"] is True
    assert "COUNT(DISTINCT ?x)" in body["sparql"]
    assert body["results"] == [{"nombre": "15"}]


def test_search_line_explicitly_connected_to_transformer():
    response = search("Quelles lignes sont reliées au poste1 ?")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert any(item["iri"] == "LigneElectrique" for item in body["analyse"]["entites"])
    assert any(item["iri"] == "poste1" and item["nature"] == "individu" for item in body["analyse"]["entites"])
    assert "?x :relie :poste1" in body["sparql"]
    assert ids(response) == ["ligneHT1", "ligneMT1"]


@pytest.mark.parametrize(
    "question",
    [
        "Quels bâtiments sont alimentés par une ligne électrique ?",
        "Quels équipements sont connectés à un poste de transformation ?",
        "Combien d'équipements sont connectés à chaque poste ?",
    ],
)
def test_search_rejects_network_questions_without_ontology_support(question):
    response = search(question)
    assert response.status_code == 400
