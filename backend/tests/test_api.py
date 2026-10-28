import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def names(results: list[dict[str, str]]) -> list[str]:
    return [row["nom"] for row in results]


def search(question: str):
    return client.post("/api/search", json={"query": question})


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_territories_list():
    response = client.get("/api/territoires-acteurs/territoires")
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {"villeTunis", "quartierLac", "quartierCentre"}


def test_territory_detail_lists_infrastructure_once():
    response = client.get("/api/territoires-acteurs/territoires/quartierLac")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["infrastructure"]]
    assert "Maison3" in ids
    assert len(ids) == len(set(ids))


def test_actor_detail():
    body = client.get("/api/territoires-acteurs/acteurs/STEG").json()
    assert body["managed_count"] == 4
    assert {item["id"] for item in body["managed_equipment"]} == {"ligne1", "ligne2", "poste1", "poste2"}


@pytest.mark.parametrize(
    "url",
    [
        "/api/territoires-acteurs/territoires/inconnu",
        "/api/territoires-acteurs/territoires/ahmed",
        "/api/territoires-acteurs/acteurs/Maison3",
        "/api/territoires-acteurs/acteurs/a%20b",
    ],
)
def test_detail_rejects_unknown_or_wrong_type(url):
    assert client.get(url).status_code == 404


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Liste les maisons autonomes qui possèdent un panneau solaire", ["Maison 3"]),
        ("maisons avec une batterie", ["Maison 3"]),
        ("maisons avec un panneau solaire", ["Maison 1", "Maison 2", "Maison 3"]),
        ("maisons sans panneau solaire", ["Maison 4", "Maison 5"]),
        ("maisons non autonomes avec un panneau solaire", ["Maison 1", "Maison 2"]),
        ("maisons avec un panneau solaire sans batterie", ["Maison 1", "Maison 2"]),
        ("maisons qui n'ont pas d'éolienne", ["Maison 1", "Maison 2", "Maison 4", "Maison 5"]),
        ("toutes les maisons", ["Maison 1", "Maison 2", "Maison 3", "Maison 4", "Maison 5"]),
    ],
)
def test_search(question, expected):
    response = search(question)
    assert response.status_code == 200
    assert names(response.json()["results"]) == expected


def test_search_interpretation_mentions_negation():
    assert search("maisons sans batterie").json()["interpretation"] == "Maisons sans batterie"


def test_search_rejects_unsupported_question():
    assert search("quelle est la météo").status_code == 400
