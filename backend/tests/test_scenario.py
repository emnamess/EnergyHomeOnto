"""Scénario de démonstration : chaque action dans l'application fait disparaître une alerte par déduction."""
import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def alert_items(alert_id: str) -> list[str]:
    alerts = {alert["id"]: alert for alert in client.get("/api/tableau-de-bord/alertes").json()}
    return [item["id"] for item in alerts[alert_id]["items"]]


def test_initial_diagnostic():
    assert sorted(alert_items("batiments-non-secourus")) == ["ecole2", "mairie2"]
    assert alert_items("fin-de-vie") == ["batterie7"]
    assert alert_items("maisons-energivores") == ["Maison16", "Maison11", "Maison10"]


def test_natural_language_question_finds_the_same_buildings():
    results = client.post("/api/search", json={"query": "bâtiments publics sans stockage"}).json()["results"]
    assert sorted(row["x"].rsplit("#", 1)[-1] for row in results) == ["ecole2", "mairie2"]


def test_actions_resolve_alerts_through_reasoning():
    # Étape 3 : une batterie de secours pour l'école -> BatimentAvecStockage est déduit.
    storage = client.post("/api/stockages", json={
        "name": "Batterie de secours – École primaire de Sahloul", "kind": "BatterieLithium",
        "capacity": 20, "charge": 100, "buildings": ["ecole2"],
    })
    assert storage.status_code == 201
    assert alert_items("batiments-non-secourus") == ["mairie2"]

    # Étape 4 : une intervention préventive -> EquipementEntretenu est déduit.
    intervention = client.post("/api/maintenance/interventions", json={
        "kind": "InterventionPreventive", "equipment": "batterie7",
        "date": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
        "description": "Remplacement préventif de l’équipement en fin de vie",
    })
    assert intervention.status_code == 201
    assert alert_items("fin-de-vie") == []

    # Étape 5 : un panneau solaire possédé par la maison -> MaisonAutonome est déduit.
    panel = client.post("/api/production/sources", json={
        "name": "Toiture solaire – Appartement Lafayette", "kind": "PanneauSolaire", "power": 4,
        "owner": "Maison16", "buildings": ["Maison16"],
    })
    assert panel.status_code == 201
    assert alert_items("maisons-energivores") == ["Maison11", "Maison10"]

    # Remise à l'état initial pour les autres tests.
    client.delete(f"/api/production/sources/{panel.json()['id']}")
    client.delete(f"/api/maintenance/interventions/{intervention.json()['id']}")
    client.delete(f"/api/stockages/{storage.json()['id']}")
    assert sorted(alert_items("batiments-non-secourus")) == ["ecole2", "mairie2"]
    assert alert_items("fin-de-vie") == ["batterie7"]
    assert alert_items("maisons-energivores") == ["Maison16", "Maison11", "Maison10"]
