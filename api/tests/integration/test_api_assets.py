"""
Integration-Tests für /assets API.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_storage_paths) -> TestClient:
    from app.main import app
    return TestClient(app)


def test_list_assets_empty(client: TestClient):
    """GET /assets ohne Assets liefert leere Liste."""
    r = client.get("/assets")
    assert r.status_code == 200
    assert r.json() == []


def test_create_asset(client: TestClient):
    """POST /assets erstellt Asset, gibt asset_id zurück."""
    r = client.post("/assets")
    assert r.status_code == 200
    data = r.json()
    assert "asset_id" in data
    assert len(data["asset_id"]) == 36


def test_get_asset_404(client: TestClient):
    """GET /assets/{id} für unbekanntes Asset -> 404."""
    r = client.get("/assets/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_deleted_asset_not_in_list(client: TestClient, sample_asset: str):
    """
    Soft-Delete: gelöschtes Asset erscheint nicht in GET /assets.
    """
    r = client.get("/assets")
    assert r.status_code == 200
    ids_before = [a["asset_id"] for a in r.json()]
    assert sample_asset in ids_before

    client.delete(f"/assets/{sample_asset}")  # Soft-Delete

    r2 = client.get("/assets")
    assert r2.status_code == 200
    ids_after = [a["asset_id"] for a in r2.json()]
    assert sample_asset not in ids_after

    r3 = client.get("/assets", params={"include_deleted": "true"})
    ids_with_deleted = [a["asset_id"] for a in r3.json()]
    assert sample_asset in ids_with_deleted


def test_delete_original_file_403(client: TestClient, sample_asset: str):
    """
    DELETE /assets/{id}/files/mesh.glb -> 403 (Original-File-Schutz).
    """
    r = client.delete(f"/assets/{sample_asset}/files/mesh.glb")
    assert r.status_code == 403
    assert "Original" in r.json().get("detail", "")


def test_step_delete_warns_on_dependencies(
    client: TestClient, sample_asset: str, tmp_storage_paths
):
    """
    DELETE /assets/{id}/steps/bgremoval ohne cascade: requires_confirmation.
    """
    from app.services import asset_service
    import json

    asset_path = asset_service.get_asset_dir(sample_asset)
    (asset_path / "image_original.png").write_bytes(b"x")
    (asset_path / "image_bgremoved.png").write_bytes(b"x")
    meta_path = asset_path / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["steps"]["image"] = {"file": "image_original.png", "provider_key": "upload"}
    meta["steps"]["bgremoval"] = {"file": "image_bgremoved.png", "provider_key": "rembg"}
    meta_path.write_text(json.dumps(meta, indent=2))

    r = client.delete(
        f"/assets/{sample_asset}/steps/bgremoval",
        params={"cascade": "false", "force": "false"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("requires_confirmation") is True
    assert "mesh" in data.get("affected_steps", [])


def test_get_asset(client: TestClient, sample_asset: str):
    """GET /assets/{id} liefert Asset-Details."""
    r = client.get(f"/assets/{sample_asset}")
    assert r.status_code == 200
    data = r.json()
    assert data["asset_id"] == sample_asset
    assert "mesh" in data["steps"]
    assert data["steps"]["mesh"]["file"] == "mesh.glb"


def test_patch_asset_meta(client: TestClient, sample_asset: str):
    """PATCH /assets/{id}/meta aktualisiert Metadaten."""
    r = client.patch(
        f"/assets/{sample_asset}/meta",
        json={"name": "Test Asset", "favorited": True, "rating": 4},
    )
    assert r.status_code == 200
    r2 = client.get(f"/assets/{sample_asset}")
    assert r2.json()["name"] == "Test Asset"
    assert r2.json()["favorited"] is True
    assert r2.json()["rating"] == 4


def test_process_sources(client: TestClient, sample_asset: str):
    """GET /assets/{id}/process/sources listet Mesh-Dateien."""
    r = client.get(f"/assets/{sample_asset}/process/sources")
    assert r.status_code == 200
    assert "mesh.glb" in r.json()["sources"]


def test_process_simplify(client: TestClient, sample_asset: str):
    """POST /assets/{id}/process/simplify erstellt vereinfachtes Mesh."""
    r = client.post(
        f"/assets/{sample_asset}/process/simplify",
        json={"source_file": "mesh.glb", "target_faces": 2},
    )
    assert r.status_code == 200
    data = r.json()
    assert "mesh_simplified_2.glb" in data.get("output_file", "")


def test_get_asset_file(client: TestClient, sample_asset: str):
    """GET /assets/{id}/files/{filename} liefert Datei."""
    r = client.get(f"/assets/{sample_asset}/files/mesh.glb")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_restore_asset(client: TestClient, sample_asset: str):
    """POST /assets/{id}/restore stellt gelöschtes Asset wieder her."""
    client.delete(f"/assets/{sample_asset}")
    r = client.post(f"/assets/{sample_asset}/restore")
    assert r.status_code == 204
    r2 = client.get("/assets")
    assert any(a["asset_id"] == sample_asset for a in r2.json())
