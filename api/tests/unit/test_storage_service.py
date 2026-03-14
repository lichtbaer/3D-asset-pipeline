"""
Unit-Tests für storage_service.
compute_storage_stats, purge_deleted.
"""

import json
import uuid

import pytest

from app.services import asset_service, storage_service


def _create_asset_with_meta(tmp_assets_dir, asset_id: str, **kwargs) -> None:
    """Hilfsfunktion: Asset mit spezifischer Metadata anlegen."""
    asset_path = tmp_assets_dir / asset_id
    asset_path.mkdir(parents=True)
    now = "2025-01-01T12:00:00.000Z"
    steps = kwargs.get("steps", {})
    meta = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": steps,
        "processing": [],
        "image_processing": [],
        "exports": kwargs.get("exports", []),
        "deleted_at": kwargs.get("deleted_at"),
    }
    (asset_path / "metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def test_get_storage_stats(tmp_storage_paths, tmp_assets_dir, sample_asset):
    """compute_storage_stats liefert asset_count, total_size_bytes, breakdown."""
    stats = storage_service.compute_storage_stats()
    assert stats["asset_count"] >= 1
    assert stats["total_size_bytes"] > 0
    assert "breakdown" in stats
    assert "total_size_human" in stats
    assert "images" in stats["breakdown"]
    assert "meshes" in stats["breakdown"]


def test_stats_excludes_deleted(tmp_storage_paths, tmp_assets_dir):
    """compute_storage_stats zählt gelöschte Assets separat (deleted_count)."""
    a1 = str(uuid.uuid4())
    a2 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={"mesh": {"file": "mesh.glb"}})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={"mesh": {"file": "mesh.glb"}})
    (tmp_assets_dir / a1 / "mesh.glb").write_bytes(b"glTF" * 10)
    (tmp_assets_dir / a2 / "mesh.glb").write_bytes(b"glTF" * 10)
    asset_service.update_metadata_fields(a2, {"deleted_at": "2025-01-01T12:00:00Z"})

    stats = storage_service.compute_storage_stats()
    assert stats["asset_count"] >= 1
    assert stats["deleted_count"] >= 1


def test_purge_deleted_removes_folders(tmp_storage_paths, tmp_assets_dir):
    """purge_deleted löscht soft-deleted Assets permanent."""
    a1 = str(uuid.uuid4())
    a2 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    asset_service.update_metadata_fields(a1, {"deleted_at": "2025-01-01T12:00:00Z"})

    result_count, result_freed = storage_service.purge_deleted()
    assert result_count >= 1
    assert result_freed >= 0
    assert not (tmp_assets_dir / a1).exists()
    assert (tmp_assets_dir / a2).exists()
