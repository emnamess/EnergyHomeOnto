import datetime
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.rdf_store import RdfStore

client = TestClient(app)
API = "/api/maintenance"
YEAR = datetime.date.today().year


# --- Équipements : lecture, calculs et filtrage -------------------------------------

def test_equipment_list_covers_every_maintainable_equipment():
    equipment = {item["id"]: item for item in client.get(f"{API}/equipements").json()}
    # EquipementMaintenable ≡ SourceEnergie ⊔ Stockage ⊔ EquipementReseau (9 sources, 5 stockages, 6 équipements réseau).
    assert len(equipment) == 20
    assert equipment["batterie1"]["category"] == "Stockage"
    assert equipment["batterie1"]["kind"] == "BatterieLithium"
    assert equipment["poste1"]["category"] == "EquipementReseau"


def test_equipment_age_and_remaining_life():
    battery = client.get(f"{API}/equipements/batterie1").json()
    # Installée en 2021, durée de vie prévue 12 ans.
    assert (battery["installation_year"], battery["lifetime_years"]) == (2021, 12)
    assert battery["age_years"] == YEAR - 2021
    assert battery["remaining_years"] == 2021 + 12 - YEAR


def test_equipment_without_installation_year_is_flagged():
    unknown = {item["id"] for item in client.get(f"{API}/equipements").json() if item["status"] == "inconnu"}
    assert unknown == {"batterie3", "groupeElectrogene1", "stockageH2_1", "superCondo1"}


def test_equipment_filters():
    storage = {item["id"] for item in client.get(f"{API}/equipements", params={"category": "Stockage"}).json()}
    assert storage == {"batterie1", "batterie2", "batterie3", "stockageH2_1", "superCondo1"}
    assert [item["id"] for item in client.get(f"{API}/equipements", params={"q": "eolienne"}).json()] == ["eolienne1", "eolienne2"]
    # batterie1 arrive en fin de vie en 2033 : c'est le premier équipement concerné.
    soon = client.get(f"{API}/equipements", params={"horizon": 2033 - YEAR}).json()
    assert [item["id"] for item in soon] == ["batterie1"]


def test_equipment_detail_uses_reasoning():
    battery = client.get(f"{API}/equipements/batterie3").json()
    # aSubi n'est pas saisi : il est déduit de concerne (owl:inverseOf).
    assert [item["id"] for item in battery["interventions"]] == ["intervention2"]
    assert battery["maintenance_cost"] == 1800.0
    # Classes définies : EquipementDejaRepare ≡ EquipementMaintenable ⊓ ∃aSubi.InterventionCorrective.
    assert battery["inferred_classes"] == ["EquipementDejaRepare"]
    assert client.get(f"{API}/equipements/eolienne1").json()["inferred_classes"] == ["EquipementEntretenu"]
    assert client.get(f"{API}/equipements/eolienne2").json()["inferred_classes"] == []


@pytest.mark.parametrize(
    "url",
    [
        f"{API}/equipements/inconnu",
        f"{API}/equipements/Maison1",
        f"{API}/equipements/ligne1",
        f"{API}/interventions/batterie1",
        f"{API}/interventions/a%20b",
    ],
)
def test_detail_rejects_unknown_or_wrong_type(url):
    assert client.get(url).status_code == 404


def test_concurrent_requests():
    # La page charge plusieurs listes en parallèle : le parseur SPARQL partagé ne doit pas planter.
    urls = [f"{API}/equipements", f"{API}/interventions", f"{API}/equipements/batterie3"] * 10
    with ThreadPoolExecutor(6) as pool:
        assert set(pool.map(lambda url: client.get(url).status_code, urls)) == {200}


# --- Interventions : lecture et filtrage --------------------------------------------

def test_intervention_list_and_filters():
    assert len(client.get(f"{API}/interventions").json()) == 5
    corrective = client.get(f"{API}/interventions", params={"kind": "InterventionCorrective"}).json()
    assert {item["id"] for item in corrective} == {"intervention2", "intervention4"}
    assert [item["id"] for item in client.get(f"{API}/interventions", params={"q": "vidange"}).json()] == ["intervention5"]
    assert [item["id"] for item in client.get(f"{API}/interventions", params={"q": "poste1"}).json()] == ["intervention4"]


# --- CRUD (SPARQL Update) ----------------------------------------------------------

def test_intervention_crud_and_journal_replay():
    planned = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    created = client.post(f"{API}/interventions", json={
        "kind": "InterventionPreventive", "equipment": "eolienne2", "date": planned,
        "cost": 900, "description": "Inspection annuelle des pales", "provider": "Maintenancier éolien",
    })
    assert created.status_code == 201
    identifier = created.json()["id"]
    assert "INSERT DATA" in created.json()["sparql"]
    detail = client.get(f"{API}/interventions/{identifier}").json()
    assert (detail["equipment_id"], detail["planned"], detail["cost"]) == ("eolienne2", True, 900.0)
    # Le raisonneur classe aussitôt l'éolienne comme équipement entretenu.
    assert client.get(f"{API}/equipements/eolienne2").json()["inferred_classes"] == ["EquipementEntretenu"]

    updated = client.put(f"{API}/interventions/{identifier}", json={
        "kind": "InterventionCorrective", "equipment": "eolienne2", "date": "2026-01-10",
        "description": "Remplacement du capteur de vent",
    })
    assert updated.status_code == 200
    detail = client.get(f"{API}/interventions/{identifier}").json()
    assert (detail["kind"], detail["cost"], detail["provider"], detail["planned"]) == ("InterventionCorrective", None, None, False)
    assert client.get(f"{API}/equipements/eolienne2").json()["inferred_classes"] == ["EquipementDejaRepare"]

    # Le journal est rejoué au démarrage : un nouveau store retrouve la modification.
    replayed = RdfStore().query(f"PREFIX : <http://www.example.org/energyhomeonto#> SELECT ?d WHERE {{ :{identifier} :descriptionIntervention ?d }}")
    assert replayed == [{"d": "Remplacement du capteur de vent"}]

    assert client.delete(f"{API}/interventions/{identifier}").status_code == 200
    assert client.get(f"{API}/interventions/{identifier}").status_code == 404
    assert client.delete(f"{API}/interventions/{identifier}").status_code == 404
    assert client.get(f"{API}/equipements/eolienne2").json()["inferred_classes"] == []


def test_intervention_input_is_escaped():
    created = client.post(f"{API}/interventions", json={
        "equipment": "poste2", "date": "2026-03-01", "description": 'Injection" } ; DROP ALL ; #',
    })
    identifier = created.json()["id"]
    assert client.get(f"{API}/interventions/{identifier}").json()["description"] == 'Injection" } ; DROP ALL ; #'
    assert client.get(f"{API}/equipements/poste2").status_code == 200
    client.delete(f"{API}/interventions/{identifier}")


@pytest.mark.parametrize(
    "payload",
    [
        {"equipment": "eolienne1", "date": "2026-03-01", "description": ""},
        {"equipment": "eolienne1", "date": "pas-une-date", "description": "Contrôle"},
        {"equipment": "eolienne1", "date": "2026-03-01", "description": "Contrôle", "cost": -5},
        {"equipment": "eolienne1", "date": "2026-03-01", "description": "Contrôle", "kind": "Maison"},
        {"equipment": "Maison1", "date": "2026-03-01", "description": "Contrôle"},
        {"equipment": "inconnu", "date": "2026-03-01", "description": "Contrôle"},
        {"equipment": "a b", "date": "2026-03-01", "description": "Contrôle"},
    ],
)
def test_intervention_input_validation(payload):
    assert client.post(f"{API}/interventions", json=payload).status_code == 422


# --- Recherche en langage naturel sur la maintenance -------------------------------

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("liste des réparations", ["intervention2", "intervention4"]),
        ("équipements déjà réparés", ["batterie3", "poste1"]),
        ("équipements entretenus", ["eolienne1", "groupeElectrogene1", "panneausolaire1"]),
        ("batteries ayant subi une réparation", ["batterie3"]),
        ("interventions qui concernent une éolienne", ["intervention3"]),
        ("éoliennes sans entretien", ["eolienne2"]),
        ("interventions avec un coût d'intervention supérieur à 1000", ["intervention2", "intervention3", "intervention4"]),
    ],
)
def test_search_maintenance(question, expected):
    response = client.post("/api/search", json={"query": question})
    assert response.status_code == 200, response.json()
    assert sorted(row["x"].rsplit("#", 1)[-1] for row in response.json()["results"]) == expected
