from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.rdf_store import RdfStore

client = TestClient(app)
API = "/api/stockages"


def ids(response) -> list[str]:
    return [item["id"] for item in response.json()]


# --- Lecture et filtrage ------------------------------------------------------------

def test_storage_list_sorted_by_capacity():
    storages = client.get(API).json()
    assert len(storages) == 11
    assert [s["id"] for s in storages][:5] == ["stockageH2_2", "stockageH2_1", "batterie7", "batterie3", "batterie1"]
    assert storages[-1]["id"] == "superCondo1"
    battery = next(s for s in storages if s["id"] == "batterie1")
    # Le type affiché est la classe la plus précise de la hiérarchie Stockage (pas EquipementEntretenu...).
    assert battery["kind"] == "BatterieLithium"
    # Énergie disponible calculée en SPARQL : capacité × niveau de charge / 100.
    assert (battery["capacity_kwh"], battery["charge_percent"], battery["available_kwh"]) == (50.0, 80.0, 40.0)
    assert (battery["source_count"], battery["building_count"]) == (2, 1)


def test_kind_filter_uses_subclass_inference():
    # batterie3 est déclarée BatteriePlomb : le raisonneur la classe aussi Batterie.
    assert sorted(ids(client.get(API, params={"kind": "Batterie"}))) == ["batterie1", "batterie2", "batterie3", "batterie4", "batterie5", "batterie6", "batterie7"]
    assert ids(client.get(API, params={"kind": "BatteriePlomb"})) == ["batterie7", "batterie3"]
    assert ids(client.get(API, params={"kind": "SuperCondensateur"})) == ["superCondo2", "superCondo1"]


def test_numeric_text_and_charge_filters():
    assert ids(client.get(API, params={"min_capacity": 50})) == ["stockageH2_2", "stockageH2_1", "batterie7", "batterie3", "batterie1"]
    assert ids(client.get(API, params={"charge": "faible"})) == ["stockageH2_2", "stockageH2_1"]
    assert sorted(ids(client.get(API, params={"charge": "moyen"}))) == ["batterie2", "batterie4", "batterie5"]
    assert sorted(ids(client.get(API, params={"charge": "eleve"}))) == ["batterie1", "batterie3", "batterie6", "batterie7", "superCondo1", "superCondo2"]
    assert ids(client.get(API, params={"q": "condo"})) == ["superCondo1"]


def test_indicators_aggregate_by_kind():
    body = client.get(f"{API}/indicateurs").json()
    assert (body["count"], body["total_capacity_kwh"], body["available_kwh"]) == (11, 1065.0, 537.17)
    lithium = next(item for item in body["by_kind"] if item["kind"] == "BatterieLithium")
    assert (lithium["count"], lithium["total_capacity_kwh"]) == (5, 102.0)


def test_storage_detail_uses_reasoning():
    battery = client.get(f"{API}/batterie1").json()
    assert {s["id"] for s in battery["sources"]} == {"eolienne1", "panneausolaire1"}
    assert [b["id"] for b in battery["buildings"]] == ["ecole1"]
    # BatimentAvecStockage ≡ Batiment ⊓ ∃estAlimentePar.Stockage, estAlimentePar déduit de alimente.
    assert battery["buildings"][0]["inferred_with_storage"] is True
    # Classes déduites : Batterie (sous-classe), Stockage, EquipementMaintenable (classe définie par union).
    assert battery["inferred_classes"] == ["Batterie", "EquipementMaintenable", "Stockage"]


def test_options_for_the_form():
    body = client.get(f"{API}/options").json()
    assert len(body["sources"]) == 23
    assert {"Maison1", "ecole1", "hopital1"} <= {b["id"] for b in body["buildings"]}


@pytest.mark.parametrize("url", [f"{API}/inconnu", f"{API}/Maison1", f"{API}/eolienne1", f"{API}/a%20b"])
def test_detail_rejects_unknown_or_wrong_type(url):
    assert client.get(url).status_code == 404


def test_concurrent_requests():
    urls = [API, f"{API}/indicateurs", f"{API}/batterie1"] * 10
    with ThreadPoolExecutor(6) as pool:
        assert set(pool.map(lambda url: client.get(url).status_code, urls)) == {200}


# --- CRUD (SPARQL Update) ----------------------------------------------------------

def test_storage_crud_and_inference():
    # Maison3 n'est alimentée par aucun stockage au départ.
    assert "Maison3" not in {b["id"] for b in client.get(f"{API}/options").json()["buildings"]
                             if "BatimentAvecStockage" in b["kind"]}
    created = client.post(API, json={
        "name": "Batterie Maison 3", "kind": "BatterieLithium", "capacity": 10, "charge": 30,
        "cycles": 4000, "lifetime": 10, "installation_year": 2025, "sources": ["eolienne1"], "buildings": ["Maison3"],
    })
    assert created.status_code == 201
    identifier = created.json()["id"]
    assert identifier == "stockageBatterieMaison3"
    assert "INSERT DATA" in created.json()["sparql"]
    detail = client.get(f"{API}/{identifier}").json()
    assert (detail["name"], detail["kind"], detail["available_kwh"]) == ("Batterie Maison 3", "BatterieLithium", 3.0)
    assert [s["id"] for s in detail["sources"]] == ["eolienne1"]
    # Le raisonneur classe aussitôt Maison3 comme BatimentAvecStockage.
    assert detail["buildings"][0]["id"] == "Maison3" and detail["buildings"][0]["inferred_with_storage"]

    updated = client.put(f"{API}/{identifier}", json={
        "name": "Supercondensateur Maison 4", "kind": "SuperCondensateur", "capacity": 4, "charge": 100, "buildings": ["Maison4"],
    })
    assert updated.status_code == 200
    assert "DELETE" in updated.json()["sparql"] and "INSERT" in updated.json()["sparql"]
    detail = client.get(f"{API}/{identifier}").json()
    assert (detail["kind"], detail["charge_cycles"], detail["sources"]) == ("SuperCondensateur", None, [])
    assert "Batterie" not in detail["inferred_classes"]
    assert [b["id"] for b in detail["buildings"]] == ["Maison4"]

    # Le journal est rejoué au démarrage : un nouveau store retrouve la modification.
    replayed = RdfStore().query(f"PREFIX : <http://www.example.org/energyhomeonto#> SELECT ?n WHERE {{ :{identifier} :nom ?n }}")
    assert replayed == [{"n": "Supercondensateur Maison 4"}]

    deleted = client.delete(f"{API}/{identifier}")
    assert deleted.status_code == 200 and "DELETE WHERE" in deleted.json()["sparql"]
    assert client.get(f"{API}/{identifier}").status_code == 404
    assert client.delete(f"{API}/{identifier}").status_code == 404


def test_storage_with_maintenance_history_cannot_be_deleted():
    # batterie3 est concernée par intervention2 (feature Maintenance).
    assert client.delete(f"{API}/batterie3").status_code == 409
    assert client.get(f"{API}/batterie3").status_code == 200


def test_storage_input_is_escaped():
    created = client.post(API, json={"name": 'Injection" } ; DROP ALL ; #', "kind": "StockageHydrogene", "capacity": 1, "charge": 0})
    identifier = created.json()["id"]
    assert client.get(f"{API}/{identifier}").json()["name"] == 'Injection" } ; DROP ALL ; #'
    assert client.get(f"{API}/batterie1").status_code == 200
    client.delete(f"{API}/{identifier}")


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "capacity": 10, "charge": 50},
        {"name": "B", "capacity": 0, "charge": 50},
        {"name": "B", "capacity": 10, "charge": 150},
        {"name": "B", "capacity": 10, "charge": -1},
        {"name": "B", "capacity": 10, "charge": 50, "kind": "Maison"},
        # nombreCyclesCharge a pour domaine Batterie : interdit sur un supercondensateur.
        {"name": "B", "capacity": 10, "charge": 50, "kind": "SuperCondensateur", "cycles": 100},
        {"name": "B", "capacity": 10, "charge": 50, "sources": ["Maison1"]},
        {"name": "B", "capacity": 10, "charge": 50, "buildings": ["eolienne1"]},
        {"name": "B", "capacity": 10, "charge": 50, "buildings": ["a b"]},
    ],
)
def test_storage_input_validation(payload):
    assert client.post(API, json=payload).status_code == 422


# --- Recherche en langage naturel sur le stockage ----------------------------------

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("supercondensateurs", ["superCondo1", "superCondo2"]),
        ("accumulateurs", ["batterie1", "batterie2", "batterie3", "batterie4", "batterie5", "batterie6", "batterie7"]),
        ("batteries au plomb", ["batterie3", "batterie7"]),
        ("stockages avec un niveau de charge inférieur à 50", ["stockageH2_1", "stockageH2_2"]),
        ("batteries avec plus de 2000 cycles", ["batterie1", "batterie2", "batterie4", "batterie5", "batterie6"]),
        ("stockages avec une durée de recharge inférieure à 1", ["superCondo1", "superCondo2"]),
        ("stockages rechargés par un panneau solaire", ["batterie1", "batterie2", "batterie4", "batterie5", "batterie6", "stockageH2_2"]),
        ("bâtiments avec batterie", ["Maison12", "Maison15", "Maison5", "Maison6", "ecole1", "hopital1", "hopital2"]),
        ("bâtiments secourus", ["Maison12", "Maison15", "Maison5", "Maison6", "ecole1", "hopital1", "hopital2", "mairie1", "supermarche2", "usine1", "usine2"]),
        ("quel est le stockage avec la plus grande capacité", ["stockageH2_2"]),
    ],
)
def test_search_storage(question, expected):
    response = client.post("/api/search", json={"query": question})
    assert response.status_code == 200, response.json()
    assert sorted(row["x"].rsplit("#", 1)[-1] for row in response.json()["results"]) == expected
