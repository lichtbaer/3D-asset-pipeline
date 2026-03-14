"""
Unit-Tests für preset_service.
Preset CRUD, compute_execution_plan, asset_to_preset_steps.
"""

import json
import uuid

import pytest

from app.services import asset_service, preset_service


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
        "processing": kwargs.get("processing", []),
        "image_processing": [],
        "exports": kwargs.get("exports", []),
        "sketchfab_upload": kwargs.get("sketchfab_upload"),
    }
    (asset_path / "metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def test_create_preset(tmp_storage_paths, tmp_presets_dir):
    """create_preset erstellt JSON-File."""
    preset = preset_service.create_preset(
        "Test Preset",
        "Beschreibung",
        [{"step": "mesh", "provider": "trellis2", "params": {}}],
    )
    assert preset["id"] is not None
    assert (tmp_presets_dir / f"{preset['id']}.json").exists()
    assert preset["name"] == "Test Preset"
    assert len(preset["steps"]) == 1


def test_list_presets(tmp_storage_paths, tmp_presets_dir):
    """list_presets liefert alle Presets."""
    preset_service.create_preset("A", "", [])
    preset_service.create_preset("B", "", [])
    presets = preset_service.list_presets()
    assert len(presets) == 2
    names = {p["name"] for p in presets}
    assert names == {"A", "B"}


def test_get_preset(tmp_storage_paths, tmp_presets_dir):
    """get_preset lädt Preset per ID."""
    created = preset_service.create_preset("Test", "Desc", [])
    loaded = preset_service.get_preset(created["id"])
    assert loaded is not None
    assert loaded["name"] == "Test"
    assert loaded["description"] == "Desc"


def test_get_preset_not_found(tmp_storage_paths):
    """get_preset mit unbekannter ID gibt None."""
    assert preset_service.get_preset("00000000-0000-0000-0000-000000000000") is None


def test_delete_preset(tmp_storage_paths, tmp_presets_dir):
    """delete_preset entfernt JSON-File."""
    preset = preset_service.create_preset("To Delete", "", [])
    result = preset_service.delete_preset(preset["id"])
    assert result is True
    assert not (tmp_presets_dir / f"{preset['id']}.json").exists()


def test_update_preset(tmp_storage_paths, tmp_presets_dir):
    """update_preset aktualisiert Name und Steps."""
    preset = preset_service.create_preset(
        "Original",
        "Desc",
        [{"step": "image", "provider": "picsart", "params": {}}],
    )
    updated = preset_service.update_preset(
        preset["id"],
        name="Updated",
        description="New Desc",
        steps=[{"step": "mesh", "provider": "trellis2", "params": {}}],
    )
    assert updated is not None
    assert updated["name"] == "Updated"
    assert updated["description"] == "New Desc"
    assert len(updated["steps"]) == 1
    assert updated["steps"][0]["step"] == "mesh"


def test_compute_execution_plan_skips_existing_steps(
    tmp_storage_paths, tmp_assets_dir, tmp_presets_dir
):
    """Asset hat mesh — mesh-Step wird übersprungen, clip_floor ist applicable."""
    asset_id = str(uuid.uuid4())
    _create_asset_with_meta(
        tmp_assets_dir,
        asset_id,
        steps={"mesh": {"file": "mesh.glb", "provider_key": "trellis2"}},
    )
    (tmp_assets_dir / asset_id / "mesh.glb").write_bytes(b"glTF")

    preset = preset_service.create_preset(
        "Test",
        "",
        [
            {"step": "mesh", "provider": "trellis2", "params": {}},
            {"step": "clip_floor", "provider": None, "params": {}},
        ],
    )

    plan, applicable, skipped = preset_service.compute_execution_plan(
        preset["id"], asset_id
    )

    assert skipped == 1
    assert applicable == 1
    assert len(plan) == 2
    assert plan[0].status == "skipped"
    assert plan[0].step == "mesh"
    assert plan[1].status == "applicable"
    assert plan[1].step == "clip_floor"


def test_compute_execution_plan_preset_not_found(tmp_storage_paths, sample_asset):
    """compute_execution_plan mit unbekanntem Preset wirft FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="nicht gefunden"):
        preset_service.compute_execution_plan(
            "00000000-0000-0000-0000-000000000000", sample_asset
        )


def test_compute_execution_plan_asset_not_found(tmp_storage_paths, tmp_presets_dir):
    """compute_execution_plan mit unbekanntem Asset wirft FileNotFoundError."""
    preset = preset_service.create_preset("Test", "", [])
    with pytest.raises(FileNotFoundError, match="nicht gefunden"):
        preset_service.compute_execution_plan(
            preset["id"], "00000000-0000-0000-0000-000000000000"
        )


def test_asset_to_preset_steps(tmp_storage_paths, tmp_assets_dir):
    """asset_to_preset_steps konvertiert Asset-Zustand in Preset-Steps."""
    asset_id = str(uuid.uuid4())
    _create_asset_with_meta(
        tmp_assets_dir,
        asset_id,
        steps={
            "image": {"file": "img.png", "provider_key": "picsart", "prompt": "dog"},
            "mesh": {"file": "mesh.glb", "provider_key": "trellis2"},
        },
        processing=[{"operation": "simplify", "params": {"target_faces": 1000}}],
    )

    meta = asset_service.get_asset(asset_id)
    assert meta is not None
    steps = preset_service.asset_to_preset_steps(meta)

    step_types = [s["step"] for s in steps]
    assert "image" in step_types
    assert "mesh" in step_types
    assert "simplify" in step_types


def test_compute_execution_plan_start_from_step(
    tmp_storage_paths, tmp_assets_dir, tmp_presets_dir
):
    """compute_execution_plan mit start_from_step überspringt frühe Steps."""
    asset_id = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, asset_id, steps={})

    preset = preset_service.create_preset(
        "Test",
        "",
        [
            {"step": "image", "provider": "picsart", "params": {}},
            {"step": "mesh", "provider": "trellis2", "params": {}},
        ],
    )

    plan, applicable, skipped = preset_service.compute_execution_plan(
        preset["id"], asset_id, start_from_step=1
    )
    assert len(plan) == 1
    assert plan[0].step == "mesh"


def test_delete_preset_invalid_id(tmp_storage_paths):
    """delete_preset mit ungültiger ID gibt False."""
    assert preset_service.delete_preset("not-a-uuid") is False
