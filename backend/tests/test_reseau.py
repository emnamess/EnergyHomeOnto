from fastapi.testclient import TestClient

from app.main import app
from app.shared.rdf_store import RdfStore

client = TestClient(app)
API = "/api/reseau"


def ids(response) -> set[str]:
    return {item["id"] for item in response.json()}


def test_network_list_and_filtering():
    response = client.get(API)
    assert response.status_code == 200
    assert {"ligneBT2", "ligneMT3", "ligneHT4", "poste1", "compteur1"} <= ids(response)
    assert "ligneBT2" in ids(client.get(API, params={"kind": "LigneBasseTension"}))
    assert ids(client.get(API, params={"kind": "PosteTransformation"})) == {"poste1", "poste2", "poste3", "poste4", "poste5"}
    assert "ligneHT3" in ids(client.get(API, params={"min_voltage": 100}))
    assert "ligneHT4" not in ids(client.get(API, params={"min_voltage": 100}))
    assert "ligneHT4" not in ids(client.get(API, params={"max_voltage": 30}))
    assert "ligneHT4" in ids(client.get(API, params={"underground": False}))
    assert ids(client.get(API, params={"q": "ligne inexistante"})) == set()


def test_network_details_and_relationships():
    line = client.get(f"{API}/ligneBT2")
    assert line.status_code == 200
    body = line.json()
    assert "LigneBasseTension" in body["kind"].split(", ")
    assert body["length"] is not None
    assert body["relationships"]
    assert body["managers"]
    assert client.get(f"{API}/poste1").json()["kind"] == "PosteTransformation"
    assert client.get(f"{API}/compteur1").json()["kind"] == "CompteurIntelligent"


def test_network_indicators_and_options():
    indicators = client.get(f"{API}/indicateurs").json()
    assert indicators["count"] == 31
    assert {item["kind"] for item in indicators["by_kind"]} >= {
        "LigneBasseTension", "LigneMoyenneTension", "LigneHauteTension", "PosteTransformation", "CompteurIntelligent",
    }
    options = client.get(f"{API}/options").json()
    assert indicators["count"] == len(options["lines"]) + len(options["equipment"])
    assert "LigneSouterraine" in options["kinds"]
    assert "STEG" in ids(type("Response", (), {"json": lambda self: options["managers"]})())
    assert "ligneBT2" in ids(type("Response", (), {"json": lambda self: options["lines"]})())


def test_network_crud_and_rdf_persistence():
    created = client.post(API, json={
        "name": "Test Ligne RDF", "kind": "LigneSouterraine", "length": 123.5, "voltage": 30,
        "section": 50, "loss_rate": 1.2, "underground": True, "installation_year": 2025,
        "related": ["Maison1"], "managers": ["STEG"],
    })
    assert created.status_code == 201, created.json()
    identifier = created.json()["id"]
    detail = client.get(f"{API}/{identifier}").json()
    assert detail["length"] == 123.5
    assert {item["id"] for item in detail["relationships"]} == {"Maison1"}
    assert {item["id"] for item in detail["managers"]} == {"STEG"}
    replayed = RdfStore().query(
        f"PREFIX : <http://www.example.org/energyhomeonto#> SELECT ?name WHERE {{ :{identifier} :nom ?name }}"
    )
    assert replayed == [{"name": "Test Ligne RDF"}]

    updated = client.put(f"{API}/{identifier}", json={
        "name": "Test Ligne RDF modifiée", "kind": "LigneElectrique", "length": 200,
        "voltage": 15, "underground": False, "related": ["Maison2"], "managers": ["STEG"],
    })
    assert updated.status_code == 200
    detail = client.get(f"{API}/{identifier}").json()
    assert detail["name"] == "Test Ligne RDF modifiée"
    assert detail["length"] == 200
    assert {item["id"] for item in detail["relationships"]} == {"Maison2"}

    deleted = client.delete(f"{API}/{identifier}")
    assert deleted.status_code == 200
    assert client.get(f"{API}/{identifier}").status_code == 404


def test_network_creation_types_validation_and_injection_protection():
    assert client.post(API, json={"name": "Wrong domain", "kind": "PosteTransformation", "length": 10}).status_code == 422
    assert client.post(API, json={"name": "Bad equipment relationship", "kind": "PosteTransformation", "related": ["Maison1"]}).status_code == 422
    assert client.post(API, json={"name": "Voltage on meter", "kind": "CompteurIntelligent", "voltage": 10}).status_code == 422
    assert client.post(API, json={"name": "Cost on line", "kind": "LigneElectrique", "installation_cost": 10}).status_code == 422
    assert client.post(API, json={"name": "Lifetime on line", "kind": "LigneElectrique", "lifetime_years": 10}).status_code == 422
    assert client.post(API, json={"name": "Underground mismatch", "kind": "LigneSouterraine", "underground": False}).status_code == 422
    assert client.post(API, json={"name": "Bad relation", "kind": "LigneElectrique", "related": ["STEG"]}).status_code == 422
    assert client.post(API, json={"name": "Bad manager", "kind": "LigneElectrique", "managers": ["Maison1"]}).status_code == 422
    assert client.post(API, json={"name": "Wrong class", "kind": "Batiment"}).status_code == 422
    assert client.get(API, params={"kind": "Batiment"}).json() == []

    payload = {"name": 'Injection" } ; DROP ALL ; #', "kind": "LigneElectrique", "length": 10}
    created = client.post(API, json=payload)
    assert created.status_code == 201
    identifier = created.json()["id"]
    assert client.get(f"{API}/{identifier}").json()["name"] == payload["name"]
    assert client.get(f"{API}/a%20b").status_code == 404
    assert client.get(f"{API}/Maison1").status_code == 404
    client.delete(f"{API}/{identifier}")


def test_network_delete_preserves_equipment_with_maintenance_history():
    assert client.delete(f"{API}/poste1").status_code == 409
