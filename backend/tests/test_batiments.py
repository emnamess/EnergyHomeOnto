from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.rdf_store import RdfStore
from app.shared.sparql import local_name

client = TestClient(app)
API = "/api/batiments"


def ids(response) -> list[str]:
    return [item["id"] for item in response.json()]


# --- Lecture et filtrage ------------------------------------------------------------

def test_building_list_all():
    response = client.get(API)
    assert response.status_code == 200
    buildings = response.json()
    assert len(buildings) == 10
    building_ids = {b["id"] for b in buildings}
    assert building_ids == {
        "Maison1", "Maison2", "Maison3", "Maison4", "Maison5",
        "ecole1", "hopital1", "mairie1", "usine1", "supermarche1",
    }


def test_building_list_filtered_by_kind():
    # Sous-classes directes
    maisons = ids(client.get(API, params={"kind": "Maison"}))
    assert sorted(maisons) == ["Maison1", "Maison2", "Maison3", "Maison4", "Maison5"]

    # Inférence rdfs:subClassOf sur BatimentPublic (Ecole, Hopital, Mairie)
    publics = ids(client.get(API, params={"kind": "BatimentPublic"}))
    assert sorted(publics) == ["ecole1", "hopital1", "mairie1"]

    # Inférence de classe définie : MaisonAutonome ≡ Maison ⊓ ∃possede.PanneauSolaire
    autonomes = ids(client.get(API, params={"kind": "MaisonAutonome"}))
    assert sorted(autonomes) == ["Maison1", "Maison2", "Maison5"]

    # Inférence de classe définie : GrosConsommateur ≡ Batiment ⊓ ∃consommation.[>= 50.0]
    gros = ids(client.get(API, params={"kind": "GrosConsommateur"}))
    assert sorted(gros) == ["hopital1", "supermarche1", "usine1"]

    # Inférence de classe définie : BatimentEconome (classe énergétique A ou B)
    economes = ids(client.get(API, params={"kind": "BatimentEconome"}))
    assert sorted(economes) == ["Maison1", "Maison2", "Maison5", "mairie1"]


def test_building_filters_energy_grid_and_consumption():
    # Classe énergétique A
    assert sorted(ids(client.get(API, params={"energy_class": "A"}))) == ["Maison1", "Maison5"]

    # Bâtiments non raccordés au réseau (seule Maison5 est autonome off-grid)
    off_grid = ids(client.get(API, params={"grid_connected": False}))
    assert off_grid == ["Maison5"]

    # Consommation minimale >= 50 kWh
    high_conso = ids(client.get(API, params={"min_consumption": 50}))
    assert sorted(high_conso) == ["hopital1", "supermarche1", "usine1"]

    # Filtre textuel
    lac = ids(client.get(API, params={"q": "hopital"}))
    assert lac == ["hopital1"]


def test_building_indicators():
    data = client.get(f"{API}/indicateurs").json()
    assert data["total_count"] == 10
    assert data["avg_consumption"] is not None
    assert data["total_surface"] is not None
    dist = {item["energy_class"]: item["count"] for item in data["energy_distribution"]}
    assert dist["A"] == 2
    assert dist["B"] == 2


# --- Détail et inférences sémantiques -----------------------------------------------

def test_building_detail_inferences_and_relations():
    res = client.get(f"{API}/Maison1")
    assert res.status_code == 200
    body = res.json()

    assert body["name"] == "Maison1"
    assert body["consumption"] == 12.0
    assert body["surface"] == 120.0
    assert body["energy_class"] == "A"
    assert body["grid_connected"] is True

    # 1. Classes inférées par le raisonneur OWL RL
    assert body["is_autonomous"] is True
    assert body["is_smart"] is True
    assert "MaisonAutonome" in body["kind"] or "MaisonAutonome" in body["inferred_classes"]
    assert "MaisonIntelligente" in body["kind"] or "MaisonIntelligente" in body["inferred_classes"]
    assert "BatimentAlimenteRenouvelable" in body["inferred_classes"]

    # 2. Propriétaire déduit par l'inverse owl:inverseOf (appartientA <-> estProprietaireDe)
    assert body["owner"] is not None
    assert body["owner"]["id"] == "ahmed"

    # 3. Localisation : transitivité de :estSitueDans (Maison1 dans quartierLac, qui est dans villeTunis)
    zone_ids = {z["id"] for z in body["zones"]}
    assert "quartierLac" in zone_ids
    assert "villeTunis" in zone_ids

    # 4. Équipements et sources
    source_ids = {s["id"] for s in body["sources"]}
    assert "panneausolaire1" in source_ids
    equipment_ids = {e["id"] for e in body["equipment"]}
    assert "compteur1" in equipment_ids


def test_building_options():
    opts = client.get(f"{API}/options").json()
    owner_ids = {o["id"] for o in opts["owners"]}
    zone_ids = {z["id"] for z in opts["zones"]}
    source_ids = {s["id"] for s in opts["sources"]}

    assert {"ahmed", "sarra", "karim"} <= owner_ids
    assert {"quartierLac", "quartierCentre", "villeTunis"} <= zone_ids
    assert {"panneausolaire1", "eolienne1"} <= source_ids


@pytest.mark.parametrize(
    "url",
    [f"{API}/inconnu", f"{API}/ahmed", f"{API}/panneausolaire1", f"{API}/a%20b"],
)
def test_detail_rejects_unknown_or_wrong_type(url):
    assert client.get(url).status_code == 404


def test_concurrent_requests():
    urls = [API, f"{API}/indicateurs", f"{API}/Maison1", f"{API}/hopital1"] * 5
    with ThreadPoolExecutor(4) as pool:
        assert set(pool.map(lambda u: client.get(u).status_code, urls)) == {200}


# --- CRUD (SPARQL Update) et inférence dynamique ------------------------------------

def test_building_crud_and_inferred_autonomous_class():
    # Création d'une nouvelle maison possédant un panneau solaire
    payload = {
        "name": "Villa Écologique Test",
        "kind": "Maison",
        "consumption": 8.5,
        "surface": 130.0,
        "occupants": 3,
        "floors": 1,
        "energy_class": "A",
        "grid_connected": False,
        "owner": "karim",
        "zone": "quartierLac",
        "sources": ["panneausolaire1"],
    }
    create_res = client.post(API, json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    identifier = created["id"]
    assert "INSERT DATA" in created["sparql"]

    # Lecture du détail : vérifier données et inférence MaisonAutonome
    detail = client.get(f"{API}/{identifier}").json()
    assert detail["name"] == "Villa Écologique Test"
    assert detail["consumption"] == 8.5
    assert detail["surface"] == 130.0
    assert detail["energy_class"] == "A"
    assert detail["grid_connected"] is False
    assert detail["owner"]["id"] == "karim"
    # Vérification que le raisonneur a inféré MaisonAutonome
    assert detail["is_autonomous"] is True
    assert "MaisonAutonome" in detail["kind"] or "MaisonAutonome" in detail["inferred_classes"]
    # Vérification de la transitivité de localisation
    assert {"quartierLac", "villeTunis"} <= {z["id"] for z in detail["zones"]}

    # Mise à jour
    update_payload = {
        **payload,
        "name": "Villa Écologique Rénovée",
        "consumption": 6.0,
        "occupants": 4,
    }
    update_res = client.put(f"{API}/{identifier}", json=update_payload)
    assert update_res.status_code == 200
    updated_detail = client.get(f"{API}/{identifier}").json()
    assert updated_detail["name"] == "Villa Écologique Rénovée"
    assert updated_detail["consumption"] == 6.0
    assert updated_detail["occupants"] == 4

    # Suppression
    del_res = client.delete(f"{API}/{identifier}")
    assert del_res.status_code == 200
    assert client.get(f"{API}/{identifier}").status_code == 404
    assert client.delete(f"{API}/{identifier}").status_code == 404


def test_building_input_is_escaped():
    payload = {
        "name": 'Maison" } ; DROP ALL ; #',
        "kind": "Maison",
        "consumption": 10.0,
    }
    create_res = client.post(API, json=payload)
    assert create_res.status_code == 201
    identifier = create_res.json()["id"]
    detail = client.get(f"{API}/{identifier}").json()
    assert detail["name"] == 'Maison" } ; DROP ALL ; #'
    client.delete(f"{API}/{identifier}")


def test_building_input_validation():
    # Nom vide
    assert client.post(API, json={"name": "", "kind": "Maison"}).status_code == 422
    # Type non autorisé
    assert client.post(API, json={"name": "Test", "kind": "Batterie"}).status_code == 422
    # Consommation négative
    assert client.post(API, json={"name": "Test", "kind": "Maison", "consumption": -5}).status_code == 422
    # Propriétaire inexistant
    assert client.post(API, json={"name": "Test", "kind": "Maison", "owner": "inconnu"}).status_code == 422
