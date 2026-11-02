import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.rdf_store import RdfStore

client = TestClient(app)
API = "/api/production"


def ids(response) -> list[str]:
    return [item["id"] for item in response.json()]


def alert_items() -> list[str]:
    alerts = {alert["id"]: alert for alert in client.get("/api/tableau-de-bord/alertes").json()}
    return [item["id"] for item in alerts["maisons-energivores"]["items"]]


# --- Lecture, filtres et inférences -------------------------------------------------

def test_source_list_sorted_by_power():
    sources = client.get(f"{API}/sources").json()
    assert len(sources) == 23
    assert [s["id"] for s in sources][:3] == ["centraleGaz2", "centraleGaz1", "panneausolaire12"]
    panel = next(s for s in sources if s["id"] == "panneausolaire1")
    assert (panel["kind"], panel["renewable"], panel["power_kw"], panel["owner"]) == ("PanneauSolaire", True, 5.0, "Maison1")


def test_filters_use_subclass_inference():
    # Renouvelable / non renouvelable : déduit de rdfs:subClassOf SourceRenouvelable / SourceNonRenouvelable.
    assert sorted(ids(client.get(f"{API}/sources", params={"renewable": "false"}))) == [
        "centraleGaz1", "centraleGaz2", "groupeElectrogene1", "groupeElectrogene2"]
    assert len(ids(client.get(f"{API}/sources", params={"renewable": "true"}))) == 19
    assert ids(client.get(f"{API}/sources", params={"kind": "CentraleHydraulique"})) == ["centraleHydro1", "centraleHydro2"]
    assert ids(client.get(f"{API}/sources", params={"min_power": 60})) == [
        "centraleGaz2", "centraleGaz1", "panneausolaire12", "centraleHydro1", "eolienne5"]
    assert ids(client.get(f"{API}/sources", params={"q": "radès"})) == ["centraleGaz2"]


def test_indicators():
    body = client.get(f"{API}/indicateurs").json()
    assert (body["count"], body["total_power_kw"], body["annual_production_mwh"]) == (23, 1122.2, 6091.0)
    assert body["renewable_share_percent"] == 17.9
    thermal = next(item for item in body["by_kind"] if item["kind"] == "CentraleThermique")
    assert (thermal["count"], thermal["total_power_kw"], thermal["renewable"]) == (2, 700.0, False)


def test_source_detail_uses_reasoning():
    farm = client.get(f"{API}/sources/panneausolaire12").json()
    assert farm["inferred_classes"] == ["SourceForte", "SourceRenouvelable"]
    assert {b["id"] for b in farm["buildings"]} == {"supermarche2", "hopital2"}
    assert [s["id"] for s in farm["storages"]] == ["stockageH2_2"]
    assert farm["zone"]["id"] == "quartierSakietEzzit"
    gas = client.get(f"{API}/sources/centraleGaz2").json()
    assert gas["fuel_type"] == "Gaz naturel"
    assert {"SourceForte", "SourcePolluante", "SourceNonRenouvelable"} <= set(gas["inferred_classes"])
    assert [o["id"] for o in client.get(f"{API}/sources/panneausolaire1").json()["owners"]] == ["Maison1"]


@pytest.mark.parametrize("url", [f"{API}/sources/inconnu", f"{API}/sources/Maison1", f"{API}/sources/a%20b"])
def test_detail_rejects_unknown_or_wrong_type(url):
    assert client.get(url).status_code == 404


def test_options_for_the_form():
    body = client.get(f"{API}/options").json()
    assert (len(body["buildings"]), len(body["storages"]), len(body["zones"])) == (27, 11, 12)


# --- CRUD (SPARQL Update) ----------------------------------------------------------

def test_source_crud_makes_house_autonomous_and_replays():
    assert "Maison10" in alert_items()
    created = client.post(f"{API}/sources", json={
        "name": "Toiture solaire Maison Khezama", "kind": "PanneauSolaire", "power": 4, "efficiency": 20,
        "panel_surface": 22, "tilt": 30, "owner": "Maison10", "buildings": ["Maison10"], "zone": "quartierKhezama",
    })
    assert created.status_code == 201 and "INSERT DATA" in created.json()["sparql"]
    identifier = created.json()["id"]
    # MaisonAutonome ≡ Maison ⊓ ∃possede.PanneauSolaire : la maison est reclassée par le raisonneur.
    assert "Maison10" not in alert_items()
    detail = client.get(f"{API}/sources/{identifier}").json()
    assert (detail["panel_surface_m2"], detail["owners"][0]["id"], detail["zone"]["id"]) == (22.0, "Maison10", "quartierKhezama")

    updated = client.put(f"{API}/sources/{identifier}", json={"name": "Éolienne Khezama", "kind": "Eolienne", "power": 3, "rotor_diameter": 4})
    assert updated.status_code == 200 and "DELETE" in updated.json()["sparql"]
    detail = client.get(f"{API}/sources/{identifier}").json()
    assert (detail["kind"], detail["panel_surface_m2"], detail["rotor_diameter_m"], detail["owners"]) == ("Eolienne", None, 4.0, [])
    assert "Maison10" in alert_items()

    replayed = RdfStore().query(f"PREFIX : <http://www.example.org/energyhomeonto#> SELECT ?n WHERE {{ :{identifier} :nom ?n }}")
    assert replayed == [{"n": "Éolienne Khezama"}]

    assert client.delete(f"{API}/sources/{identifier}").status_code == 200
    assert client.get(f"{API}/sources/{identifier}").status_code == 404
    assert client.delete(f"{API}/sources/{identifier}").status_code == 404


def test_source_with_maintenance_history_cannot_be_deleted():
    assert client.delete(f"{API}/sources/eolienne1").status_code == 409
    assert client.get(f"{API}/sources/eolienne1").status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "kind": "PanneauSolaire", "power": 1},
        {"name": "X", "kind": "Maison", "power": 1},
        {"name": "X", "kind": "PanneauSolaire", "power": 0},
        {"name": "X", "kind": "PanneauSolaire", "power": 1, "efficiency": 120},
        {"name": "X", "kind": "Eolienne", "power": 1, "fuel_type": "Diesel"},
        {"name": "X", "kind": "PanneauSolaire", "power": 1, "rotor_diameter": 3},
        {"name": "X", "kind": "PanneauSolaire", "power": 1, "owner": "eolienne1"},
        {"name": "X", "kind": "PanneauSolaire", "power": 1, "storages": ["Maison1"]},
    ],
)
def test_source_input_validation(payload):
    assert client.post(f"{API}/sources", json=payload).status_code == 422


def test_source_input_is_escaped():
    created = client.post(f"{API}/sources", json={
        "name": 'Injection" } ; DROP ALL ; #', "kind": "GroupeElectrogene", "power": 1, "fuel_type": 'Diesel" }',
    })
    identifier = created.json()["id"]
    detail = client.get(f"{API}/sources/{identifier}").json()
    assert (detail["name"], detail["fuel_type"]) == ('Injection" } ; DROP ALL ; #', 'Diesel" }')
    assert client.get(f"{API}/sources/eolienne1").status_code == 200
    client.delete(f"{API}/sources/{identifier}")


# --- Recherche en langage naturel sur la production ---------------------------------

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("sources fossiles", ["centraleGaz1", "centraleGaz2", "groupeElectrogene1", "groupeElectrogene2"]),
        ("sources polluantes", ["centraleGaz1", "centraleGaz2", "groupeElectrogene1", "groupeElectrogene2"]),
        ("sources à haut rendement", ["centraleHydro1", "centraleHydro2"]),
        ("quelle source produit le plus", ["centraleGaz2"]),
        ("panneaux installés après 2022", ["panneausolaire10", "panneausolaire12", "panneausolaire3", "panneausolaire4", "panneausolaire7", "panneausolaire9"]),
        ("sources installées avant 2000", ["centraleHydro1", "centraleHydro2"]),
        ("panneaux solaires qui alimentent une école", ["panneausolaire10"]),
        ("quel bâtiment consomme le moins", ["Maison12"]),
    ],
)
def test_search_production(question, expected):
    response = client.post("/api/search", json={"query": question})
    assert response.status_code == 200, response.json()
    assert sorted(row["x"].rsplit("#", 1)[-1] for row in response.json()["results"]) == expected
