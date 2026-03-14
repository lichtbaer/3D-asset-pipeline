"""
Pytest-Fixtures für Purzel ML Asset Pipeline Tests.
- Test-Client: FastAPI TestClient
- tmp-asset-dir: Temporäres Asset-Verzeichnis
- Mock-Provider: Externe API-Calls werden gemockt (respx)
"""

import json
import os
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Storage/Log-Pfade vor App-Import setzen (für Integration-Tests)
_test_tmp = Path(tempfile.gettempdir()) / "purzel-test"
_test_tmp.mkdir(parents=True, exist_ok=True)
(_test_tmp / "logs").mkdir(exist_ok=True)
# Überschreiben für Tests (nicht setdefault, damit Docker-Env ignoriert wird)
os.environ["LOG_PATH"] = str(_test_tmp / "logs")
os.environ["ASSETS_STORAGE_PATH"] = str(_test_tmp / "assets")
os.environ["PRESETS_STORAGE_PATH"] = str(_test_tmp / "presets")
os.environ["MESH_STORAGE_PATH"] = str(_test_tmp / "meshes")
os.environ["BGREMOVAL_STORAGE_PATH"] = str(_test_tmp / "bgremoval")
os.environ["ANIMATION_STORAGE_PATH"] = str(_test_tmp / "animations")
os.environ["IMAGE_STORAGE_PATH"] = str(_test_tmp / "images")


@pytest.fixture
def tmp_asset_dir() -> Path:
    """Temporäres Verzeichnis für Asset-Tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def tmp_assets_dir(tmp_path: Path) -> Path:
    """Temporäres ASSETS_STORAGE_PATH für Asset-Service-Tests."""
    assets = tmp_path / "assets"
    assets.mkdir(parents=True)
    return assets


@pytest.fixture
def tmp_presets_dir(tmp_path: Path) -> Path:
    """Temporäres PRESETS_STORAGE_PATH."""
    presets = tmp_path / "presets"
    presets.mkdir(parents=True)
    return presets


@pytest.fixture
def tmp_storage_paths(tmp_assets_dir: Path, tmp_presets_dir: Path, monkeypatch):
    """Überschreibt Storage-Pfade für Tests. Patched dort wo sie importiert werden."""
    meshes = tmp_assets_dir.parent / "meshes"
    bgremoval = tmp_assets_dir.parent / "bgremoval"
    animations = tmp_assets_dir.parent / "animations"
    images = tmp_assets_dir.parent / "images"
    for p in (meshes, bgremoval, animations, images):
        p.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.config.storage.ASSETS_STORAGE_PATH", tmp_assets_dir)
    monkeypatch.setattr("app.config.storage.PRESETS_STORAGE_PATH", tmp_presets_dir)
    monkeypatch.setattr("app.config.storage.MESH_STORAGE_PATH", meshes)
    monkeypatch.setattr("app.config.storage.BGREMOVAL_STORAGE_PATH", bgremoval)
    monkeypatch.setattr("app.config.storage.ANIMATION_STORAGE_PATH", animations)
    monkeypatch.setattr("app.config.storage.IMAGE_STORAGE_PATH", images)

    # AssetPaths und asset_service nutzen ASSETS_STORAGE_PATH
    monkeypatch.setattr("app.core.asset_paths.ASSETS_STORAGE_PATH", tmp_assets_dir)
    monkeypatch.setattr("app.services.asset_service.ASSETS_STORAGE_PATH", tmp_assets_dir)
    monkeypatch.setattr("app.services.preset_service.PRESETS_STORAGE_PATH", tmp_presets_dir)
    return tmp_assets_dir


@pytest.fixture
def sample_asset(tmp_storage_paths: Path, tmp_assets_dir: Path) -> str:
    """Erstellt ein Asset mit minimaler metadata.json und mesh.glb."""
    asset_id = str(uuid.uuid4())
    asset_path = tmp_assets_dir / asset_id
    asset_path.mkdir(parents=True)

    # Minimales GLB mit trimesh
    import trimesh
    import numpy as np
    verts = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=np.float32)
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    mesh_path = asset_path / "mesh.glb"
    mesh.export(str(mesh_path))

    now = "2025-01-01T12:00:00.000Z"
    metadata = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": {
            "mesh": {
                "job_id": "test",
                "provider_key": "upload",
                "file": "mesh.glb",
                "generated_at": now,
            },
        },
        "processing": [],
        "image_processing": [],
        "exports": [],
    }
    (asset_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return asset_id


@pytest.fixture
def sample_asset_with_image(tmp_storage_paths: Path, tmp_assets_dir: Path) -> str:
    """Erstellt ein Asset mit Bild (PNG für Image-Processing)."""
    from PIL import Image
    asset_id = str(uuid.uuid4())
    asset_path = tmp_assets_dir / asset_id
    asset_path.mkdir(parents=True)

    # 100x100 PNG
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    img.save(asset_path / "image_original.png", "PNG")

    now = "2025-01-01T12:00:00.000Z"
    metadata = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": {
            "image": {
                "job_id": "test",
                "provider_key": "upload",
                "file": "image_original.png",
                "generated_at": now,
            },
        },
        "processing": [],
        "image_processing": [],
    }
    (asset_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return asset_id


@pytest.fixture
def test_client():
    """FastAPI TestClient."""

    def _client():
        from app.main import app
        return TestClient(app)

    return _client


@pytest.fixture
def client(test_client) -> TestClient:
    """TestClient-Instanz."""
    return test_client()
