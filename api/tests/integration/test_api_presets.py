"""
Integration-Tests für /presets API.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_storage_paths) -> TestClient:
    from app.main import app
    return TestClient(app)


def test_list_presets_empty(client: TestClient):
    """GET /presets ohne Presets -> leere Liste."""
    r = client.get("/presets")
    assert r.status_code == 200
    assert r.json() == []


def test_create_preset(client: TestClient):
    """POST /presets erstellt Preset."""
    r = client.post(
        "/presets",
        json={
            "name": "Test Preset",
            "description": "Beschreibung",
            "steps": [
                {"step": "image", "provider": "picsart", "params": {"prompt": "test"}},
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Preset"
    assert "id" in data
    assert len(data["steps"]) == 1


def test_get_preset_404(client: TestClient):
    """GET /presets/{id} für unbekanntes Preset -> 404."""
    r = client.get("/presets/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_apply_preset_404_asset(client: TestClient):
    """POST /presets/{id}/apply mit unbekanntem Asset -> 404."""
    # Erst Preset erstellen
    cr = client.post(
        "/presets",
        json={
            "name": "P",
            "description": "",
            "steps": [{"step": "image", "provider": None, "params": {}}],
        },
    )
    preset_id = cr.json()["id"]

    r = client.post(
        f"/presets/{preset_id}/apply",
        json={
            "asset_id": "00000000-0000-0000-0000-000000000000",
            "start_from_step": 0,
        },
    )
    assert r.status_code == 404
