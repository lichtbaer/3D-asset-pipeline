"""
Unit-Tests für asset_service.
Kritisch: Soft-Delete, Original-File-Schutz, Step-Delete-Warnung.
"""

import json

import pytest

from app.services import asset_service


def test_deleted_asset_not_in_list(tmp_storage_paths, sample_asset: str):
    """
    Soft-Delete: gelöschtes Asset erscheint nicht in list_assets(include_deleted=False).
    """
    assets_before = asset_service.list_assets(include_deleted=False)
    assert any(a.asset_id == sample_asset for a in assets_before)

    asset_service.soft_delete_asset(sample_asset)

    assets_after = asset_service.list_assets(include_deleted=False)
    assert not any(a.asset_id == sample_asset for a in assets_after)

    assets_with_deleted = asset_service.list_assets(include_deleted=True)
    assert any(a.asset_id == sample_asset for a in assets_with_deleted)


def test_cannot_delete_original_mesh_file(tmp_storage_paths, sample_asset: str):
    """
    Original-File-Schutz: mesh.glb kann nicht via delete_asset_file gelöscht werden.
    """
    with pytest.raises(PermissionError, match="Original-Datei.*nicht einzeln gelöscht"):
        asset_service.delete_asset_file(sample_asset, "mesh.glb")


def test_cannot_delete_image_bgremoved(tmp_storage_paths, sample_asset_with_image: str):
    """image_bgremoved.png ist protected (PROTECTED_FILENAMES)."""
    asset_path = asset_service.get_asset_dir(sample_asset_with_image)
    (asset_path / "image_bgremoved.png").write_bytes(b"fake")
    meta = asset_service.get_asset(sample_asset_with_image)
    meta_dict = {k: v for k, v in meta.to_dict().items()}
    meta_dict["steps"] = {**meta.steps, "bgremoval": {"file": "image_bgremoved.png"}}
    (asset_path / "metadata.json").write_text(
        json.dumps(meta_dict, indent=2), encoding="utf-8"
    )

    with pytest.raises(PermissionError, match="Original-Datei"):
        asset_service.delete_asset_file(sample_asset_with_image, "image_bgremoved.png")


def test_step_delete_warns_on_downstream_dependencies(
    tmp_storage_paths, sample_asset: str
):
    """
    Step-Löschung: Bei Abhängigkeiten (ohne cascade/force) wird requires_confirmation.
    """
    # Asset mit image + bgremoval + mesh (mesh hängt von bgremoval ab)
    asset_path = asset_service.get_asset_dir(sample_asset)
    meta_path = asset_path / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["steps"]["image"] = {"file": "image_original.png", "provider_key": "upload"}
    meta["steps"]["bgremoval"] = {"file": "image_bgremoved.png", "provider_key": "rembg"}
    meta_path.write_text(json.dumps(meta, indent=2))
    (asset_path / "image_original.png").write_bytes(b"x")
    (asset_path / "image_bgremoved.png").write_bytes(b"x")

    result = asset_service.delete_step(
        sample_asset, "bgremoval", cascade=False, force=False
    )

    assert result.get("requires_confirmation") is True
    assert "mesh" in result.get("affected_steps", [])
    assert "basieren auf diesem Step" in result.get("message", "")


def test_create_asset_returns_uuid(tmp_storage_paths):
    """create_asset gibt gültige UUID zurück."""
    asset_id = asset_service.create_asset()
    assert len(asset_id) == 36
    assert asset_id.count("-") == 4
    meta = asset_service.get_asset(asset_id)
    assert meta is not None
    assert meta.asset_id == asset_id


def test_get_file_path_validates_asset_id(tmp_storage_paths):
    """Path-Traversal: ungültige asset_id gibt None."""
    assert asset_service.get_file_path("../../../etc/passwd", "x") is None
    assert asset_service.get_file_path("not-a-uuid", "mesh.glb") is None


def test_append_processing_entry(tmp_storage_paths, sample_asset: str):
    """append_processing_entry fügt Eintrag hinzu."""
    meta_before = asset_service.get_asset(sample_asset)
    len_before = len(meta_before.processing)

    asset_service.append_processing_entry(
        sample_asset,
        {"operation": "simplify", "params": {"target_faces": 100}, "output_file": "x.glb"},
    )

    meta_after = asset_service.get_asset(sample_asset)
    assert len(meta_after.processing) == len_before + 1
    assert meta_after.processing[-1]["operation"] == "simplify"
