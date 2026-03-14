"""
Unit-Tests für asset_service.
Kritisch: Soft-Delete, Original-File-Schutz, Step-Delete-Warnung.
"""

import json
import uuid

import pytest

from app.services import asset_service


@pytest.mark.asyncio
async def test_update_step_writes_file_and_metadata(tmp_storage_paths, sample_asset):
    """update_step schreibt Datei und aktualisiert metadata."""
    await asset_service.update_step(
        sample_asset,
        "mesh",
        {"job_id": "j1", "provider_key": "test"},
        file_bytes=b"glTFmesh",
        filename="mesh.glb",
    )
    meta = asset_service.get_asset(sample_asset)
    assert "mesh" in meta.steps
    assert meta.steps["mesh"].get("file") == "mesh.glb"


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


def test_cannot_delete_image_original(tmp_storage_paths, sample_asset_with_image: str):
    """image_original.* ist protected (Original-Output)."""
    with pytest.raises(PermissionError, match="Original-Datei"):
        asset_service.delete_asset_file(sample_asset_with_image, "image_original.png")


def test_cannot_delete_file_referenced_in_step(tmp_storage_paths, tmp_assets_dir):
    """Datei die in steps referenziert ist, kann nicht gelöscht werden."""
    a1 = str(uuid.uuid4())
    asset_path = tmp_assets_dir / a1
    asset_path.mkdir(parents=True)
    (asset_path / "custom_mesh.glb").write_bytes(b"glTF")
    meta = {
        "asset_id": a1,
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "steps": {"mesh": {"file": "custom_mesh.glb", "provider_key": "x"}},
        "processing": [],
        "image_processing": [],
        "exports": [],
    }
    (asset_path / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    with pytest.raises(PermissionError, match="Original-Datei"):
        asset_service.delete_asset_file(a1, "custom_mesh.glb")


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


def test_get_file_path_rejects_path_traversal(tmp_storage_paths, sample_asset):
    """get_file_path gibt None bei Path-Traversal in filename."""
    path = asset_service.get_file_path(sample_asset, "../../../etc/passwd")
    assert path is None


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


def _create_asset_with_meta(
    tmp_assets_dir,
    asset_id: str,
    *,
    tags: list[str] | None = None,
    steps: dict | None = None,
    prompt: str | None = None,
    deleted: bool = False,
    rating: int | None = None,
    favorited: bool | None = None,
) -> None:
    """Hilfsfunktion: Asset mit spezifischer Metadata anlegen."""
    asset_path = tmp_assets_dir / asset_id
    asset_path.mkdir(parents=True)
    now = "2025-01-01T12:00:00.000Z"
    steps = steps or {}
    if prompt:
        steps.setdefault("image", {})["prompt"] = prompt
    meta = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": steps,
        "processing": [],
        "image_processing": [],
        "exports": [],
        "tags": tags or [],
    }
    if deleted:
        meta["deleted_at"] = now
    if rating is not None:
        meta["rating"] = rating
    if favorited is not None:
        meta["favorited"] = favorited
    (asset_path / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def test_list_assets_filter_by_tag(tmp_storage_paths, tmp_assets_dir):
    """list_assets filtert nach Tags (comma-separated)."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, tags=["purzel", "dog"])
    _create_asset_with_meta(tmp_assets_dir, a2, tags=["cat"])
    assets = asset_service.list_assets(tags="purzel")
    assert len(assets) == 1
    assert assets[0].asset_id == a1


def test_list_assets_filter_has_step(tmp_storage_paths, tmp_assets_dir):
    """list_assets filtert nach vorhandenem Step."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(
        tmp_assets_dir, a1, steps={"mesh": {"file": "mesh.glb", "provider_key": "x"}}
    )
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    assets = asset_service.list_assets(has_step="mesh")
    assert len(assets) == 1
    assert assets[0].asset_id == a1


def test_list_assets_search_by_prompt(tmp_storage_paths, tmp_assets_dir):
    """list_assets sucht in Prompt."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(
        tmp_assets_dir, a1, steps={"image": {"prompt": "armored dog T-pose"}}
    )
    _create_asset_with_meta(
        tmp_assets_dir, a2, steps={"image": {"prompt": "cat wizard"}}
    )
    assets = asset_service.list_assets(search="dog")
    assert len(assets) == 1
    assert assets[0].asset_id == a1


def test_delete_asset_soft(tmp_storage_paths, tmp_assets_dir):
    """Soft-Delete: deleted_at gesetzt, Ordner bleibt."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1)
    asset_service.delete_asset(a1, permanent=False)
    meta = asset_service.get_asset(a1)
    assert meta is not None
    assert meta.deleted_at is not None
    assert (tmp_assets_dir / a1).exists()


def test_delete_asset_permanent(tmp_storage_paths, tmp_assets_dir):
    """Permanent-Delete: Ordner wird gelöscht."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1)
    asset_service.delete_asset(a1, permanent=True)
    assert not (tmp_assets_dir / a1).exists()


def test_update_asset_meta(tmp_storage_paths, tmp_assets_dir):
    """update_asset_meta aktualisiert Name, Tags, Rating."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1)
    asset_service.update_asset_meta(
        a1, name="Purzel v3", tags=["purzel"], rating=4
    )
    meta = asset_service.get_asset(a1)
    assert meta is not None
    assert meta.name == "Purzel v3"
    assert meta.rating == 4
    assert "purzel" in meta.tags


def test_get_all_tags(tmp_storage_paths, tmp_assets_dir):
    """get_all_tags liefert alle verwendeten Tags."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, tags=["purzel", "dog"])
    _create_asset_with_meta(tmp_assets_dir, a2, tags=["cat", "purzel"])
    tags = asset_service.get_all_tags()
    assert "purzel" in tags
    assert "dog" in tags
    assert "cat" in tags
    assert len(tags) == 3


def test_restore_asset(tmp_storage_paths, tmp_assets_dir):
    """restore_asset stellt soft-deleted Asset wieder her."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, deleted=True)
    result = asset_service.restore_asset(a1)
    assert result is True
    meta = asset_service.get_asset(a1)
    assert meta is not None
    assert meta.deleted_at is None


def test_delete_asset_invalid_id(tmp_storage_paths):
    """delete_asset mit ungültiger UUID gibt False."""
    assert asset_service.delete_asset("not-a-uuid", permanent=False) is False


def test_list_assets_sort_options(tmp_storage_paths, tmp_assets_dir):
    """list_assets unterstützt created_asc, name, rating Sortierung."""
    a1, a2, a3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(
        tmp_assets_dir, a1,
        steps={},
        tags=[],
    )
    _create_asset_with_meta(tmp_assets_dir, a2, steps={}, tags=[])
    _create_asset_with_meta(tmp_assets_dir, a3, steps={}, tags=[])
    asset_service.update_asset_meta(a1, name="Zebra")
    asset_service.update_asset_meta(a2, name="Alpha")
    asset_service.update_asset_meta(a3, name="Beta", rating=5)

    by_name = asset_service.list_assets(sort="name")
    assert len(by_name) >= 3
    names = [a.name or "" for a in by_name if a.asset_id in (a1, a2, a3)]
    assert "Alpha" in names and "Beta" in names and "Zebra" in names

    by_rating = asset_service.list_assets(sort="rating")
    assert len(by_rating) >= 3


def test_list_assets_sort_by_name(tmp_storage_paths, tmp_assets_dir):
    """list_assets mit sort=name sortiert alphabetisch nach Name."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    asset_service.update_asset_meta(a1, name="Zebra")
    asset_service.update_asset_meta(a2, name="Alpha")
    assets = asset_service.list_assets(sort="name")
    ids_in_order = [a.asset_id for a in assets if a.asset_id in (a1, a2)]
    assert ids_in_order[0] == a2  # Alpha vor Zebra
    assert ids_in_order[1] == a1


def test_list_assets_search_motion_prompt(tmp_storage_paths, tmp_assets_dir):
    """list_assets sucht in motion_prompt (Animation)."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(
        tmp_assets_dir, a1,
        steps={"animation": {"motion_prompt": "walking dog", "file": "x.glb"}},
    )
    _create_asset_with_meta(
        tmp_assets_dir, a2,
        steps={"animation": {"motion_prompt": "running cat", "file": "y.glb"}},
    )
    assets = asset_service.list_assets(search="walking")
    assert len(assets) == 1
    assert assets[0].asset_id == a1


def test_get_asset_returns_none_for_missing(tmp_storage_paths):
    """get_asset gibt None für nicht existierendes Asset."""
    result = asset_service.get_asset("00000000-0000-0000-0000-000000000000")
    assert result is None


def test_list_mesh_files_empty_dir(tmp_storage_paths, tmp_assets_dir):
    """list_mesh_files gibt leere Liste wenn kein GLB vorhanden."""
    a1 = str(uuid.uuid4())
    asset_path = tmp_assets_dir / a1
    asset_path.mkdir(parents=True)
    (asset_path / "metadata.json").write_text(
        json.dumps({"asset_id": a1, "steps": {}, "created_at": "x", "updated_at": "x"}),
        encoding="utf-8",
    )
    files = asset_service.list_mesh_files(a1)
    assert files == []


def test_list_mesh_files_returns_empty_when_asset_dir_missing(tmp_storage_paths):
    """list_mesh_files gibt [] wenn Asset-Ordner nicht existiert."""
    result = asset_service.list_mesh_files("00000000-0000-0000-0000-000000000000")
    assert result == []


def test_list_image_files_empty_dir(tmp_storage_paths, tmp_assets_dir):
    """list_image_files gibt leere Liste wenn kein Bild vorhanden."""
    a1 = str(uuid.uuid4())
    asset_path = tmp_assets_dir / a1
    asset_path.mkdir(parents=True)
    (asset_path / "metadata.json").write_text(
        json.dumps({"asset_id": a1, "steps": {}, "created_at": "x", "updated_at": "x"}),
        encoding="utf-8",
    )
    files = asset_service.list_image_files(a1)
    assert files == []


def test_write_asset_file_raises_when_asset_not_exists(tmp_storage_paths):
    """write_asset_file wirft FileNotFoundError wenn Asset nicht existiert."""
    with pytest.raises(FileNotFoundError, match="existiert nicht"):
        asset_service.write_asset_file("00000000-0000-0000-0000-000000000000", "x.txt", b"x")


def test_list_assets_filter_favorited(tmp_storage_paths, tmp_assets_dir):
    """list_assets filtert nach favorited."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    asset_service.update_asset_meta(a1, favorited=True)

    fav = asset_service.list_assets(favorited=True)
    assert any(a.asset_id == a1 for a in fav)
    assert not any(a.asset_id == a2 for a in fav)


def test_list_assets_filter_rating(tmp_storage_paths, tmp_assets_dir):
    """list_assets filtert nach rating_min."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    asset_service.update_asset_meta(a1, rating=5)
    asset_service.update_asset_meta(a2, rating=2)

    assets = asset_service.list_assets(rating=4)
    assert any(a.asset_id == a1 for a in assets)
    assert not any(a.asset_id == a2 for a in assets)


def test_list_assets_sort_by_rating(tmp_storage_paths, tmp_assets_dir):
    """list_assets sortiert nach rating (höchste zuerst)."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={}, rating=5)
    _create_asset_with_meta(tmp_assets_dir, a2, steps={}, rating=2)
    assets = asset_service.list_assets(sort="rating")
    ids = [a.asset_id for a in assets if a.asset_id in (a1, a2)]
    assert ids[0] == a1
    assert ids[1] == a2


def test_get_all_tags_deduplicates(tmp_storage_paths, tmp_assets_dir):
    """get_all_tags liefert sortierte, deduplizierte Tags."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, tags=["purzel", "dog"])
    _create_asset_with_meta(tmp_assets_dir, a2, tags=["dog", "cat"])
    tags = asset_service.get_all_tags()
    assert sorted(tags) == ["cat", "dog", "purzel"]


def test_delete_step_without_cascade_warns(tmp_storage_paths, tmp_assets_dir):
    """delete_step ohne cascade gibt requires_confirmation wenn abhängige Steps existieren."""
    a1 = str(uuid.uuid4())
    asset_path = tmp_assets_dir / a1
    asset_path.mkdir(parents=True)
    meta = {
        "asset_id": a1,
        "created_at": "2025-01-01T12:00:00.000Z",
        "updated_at": "2025-01-01T12:00:00.000Z",
        "steps": {
            "mesh": {"file": "mesh.glb", "provider_key": "x"},
            "rigging": {"file": "mesh_rigged.glb", "provider_key": "x"},
            "animation": {"file": "mesh_animated.glb", "provider_key": "x"},
        },
        "processing": [],
        "image_processing": [],
        "exports": [],
    }
    (asset_path / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (asset_path / "mesh.glb").write_bytes(b"glTF")
    (asset_path / "mesh_rigged.glb").write_bytes(b"glTF")
    (asset_path / "mesh_animated.glb").write_bytes(b"glTF")

    result = asset_service.delete_step(a1, "mesh", cascade=False)
    assert result["requires_confirmation"] is True
    assert "rigging" in result["affected_steps"]
    assert "animation" in result["affected_steps"]


def test_get_or_create_asset_id(tmp_storage_paths, tmp_assets_dir):
    """get_or_create_asset_id gibt bestehendes zurück oder erstellt neues."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    result = asset_service.get_or_create_asset_id(a1)
    assert result == a1

    result_new = asset_service.get_or_create_asset_id(None)
    assert result_new is not None
    assert len(result_new) == 36


def test_create_asset_from_image_upload(tmp_storage_paths, tmp_assets_dir):
    """create_asset_from_image_upload erstellt Asset aus Bild-Bytes."""
    asset_id = asset_service.create_asset_from_image_upload(
        b"\x89PNG\r\n\x1a\n" + b"x" * 100,
        "test.png",
        name="My Image",
    )
    assert asset_id is not None
    meta = asset_service.get_asset(asset_id)
    assert meta is not None
    assert meta.source == "upload"
    assert "image" in meta.steps
    assert meta.steps["image"].get("provider_key") == "upload"


def test_create_asset_from_image_upload_jpg(tmp_storage_paths, tmp_assets_dir):
    """create_asset_from_image_upload mit JPG speichert als image_original.jpg."""
    asset_id = asset_service.create_asset_from_image_upload(
        b"\xff\xd8\xff" + b"x" * 100,
        "photo.jpg",
        name="Photo",
    )
    meta = asset_service.get_asset(asset_id)
    assert meta is not None
    assert "image_original.jpg" in meta.steps["image"].get("file", "")


def test_create_asset_from_mesh_upload_glb(tmp_storage_paths, tmp_assets_dir):
    """create_asset_from_mesh_upload mit GLB erstellt Asset."""
    import numpy as np
    import trimesh

    verts = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=np.float32)
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    glb_bytes = mesh.export(file_type="glb")
    if isinstance(glb_bytes, str):
        glb_bytes = glb_bytes.encode("utf-8")
    elif isinstance(glb_bytes, dict):
        glb_bytes = json.dumps(glb_bytes).encode("utf-8")

    asset_id = asset_service.create_asset_from_mesh_upload(
        glb_bytes, "model.glb", name="Test Mesh"
    )
    meta = asset_service.get_asset(asset_id)
    assert meta is not None
    assert meta.source == "upload"
    assert "mesh" in meta.steps
    assert meta.steps["mesh"].get("file") == "mesh.glb"


def test_list_mesh_files(tmp_storage_paths, sample_asset):
    """list_mesh_files listet GLB-Dateien."""
    asset_path = asset_service.get_asset_dir(sample_asset)
    (asset_path / "extra.glb").write_bytes(b"glTF")
    files = asset_service.list_mesh_files(sample_asset)
    assert "mesh.glb" in files
    assert "extra.glb" in files


def test_list_image_files(tmp_storage_paths, sample_asset_with_image):
    """list_image_files listet Bild-Dateien."""
    asset_path = asset_service.get_asset_dir(sample_asset_with_image)
    (asset_path / "extra.jpg").write_bytes(b"\xff\xd8\xff")
    files = asset_service.list_image_files(sample_asset_with_image)
    assert "image_original.png" in files
    assert "extra.jpg" in files


def test_write_asset_file(tmp_storage_paths, sample_asset):
    """write_asset_file schreibt Datei in Asset-Ordner."""
    asset_service.write_asset_file(sample_asset, "test.txt", b"hello")
    path = asset_service.get_asset_dir(sample_asset) / "test.txt"
    assert path.read_bytes() == b"hello"


def test_update_metadata_fields(tmp_storage_paths, tmp_assets_dir):
    """update_metadata_fields aktualisiert Top-Level-Felder."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    asset_service.update_metadata_fields(
        a1, {"source": "sketchfab", "sketchfab_uid": "abc123"}
    )
    meta = asset_service.get_asset(a1)
    assert meta is not None
    assert meta.source == "sketchfab"
    assert meta.sketchfab_uid == "abc123"


def test_append_image_processing_entry(tmp_storage_paths, sample_asset):
    """append_image_processing_entry fügt Eintrag hinzu."""
    meta_before = asset_service.get_asset(sample_asset)
    len_before = len(meta_before.image_processing)
    asset_service.append_image_processing_entry(
        sample_asset,
        {"operation": "resize", "output_file": "resized.png", "params": {}},
    )
    meta_after = asset_service.get_asset(sample_asset)
    assert len(meta_after.image_processing) == len_before + 1


def test_delete_asset_file_processing_output(tmp_storage_paths, sample_asset):
    """delete_asset_file löscht processing-Output und bereinigt Metadata."""
    asset_service.append_processing_entry(
        sample_asset,
        {"operation": "simplify", "output_file": "mesh_simplified_100.glb", "params": {}},
    )
    asset_path = asset_service.get_asset_dir(sample_asset)
    (asset_path / "mesh_simplified_100.glb").write_bytes(b"glTF")
    result = asset_service.delete_asset_file(sample_asset, "mesh_simplified_100.glb")
    assert result is True
    assert not (asset_path / "mesh_simplified_100.glb").exists()
    meta = asset_service.get_asset(sample_asset)
    assert not any(e.get("output_file") == "mesh_simplified_100.glb" for e in meta.processing)


def test_delete_asset_file_image_processing_entry(tmp_storage_paths, sample_asset_with_image):
    """delete_asset_file entfernt image_processing-Einträge."""
    asset_service.append_image_processing_entry(
        sample_asset_with_image,
        {"operation": "crop", "output_file": "image_cropped.png", "params": {}},
    )
    asset_path = asset_service.get_asset_dir(sample_asset_with_image)
    (asset_path / "image_cropped.png").write_bytes(b"PNG")
    result = asset_service.delete_asset_file(sample_asset_with_image, "image_cropped.png")
    assert result is True
    meta = asset_service.get_asset(sample_asset_with_image)
    assert not any(e.get("output_file") == "image_cropped.png" for e in meta.image_processing)


def test_delete_asset_file_removes_export_entry(tmp_storage_paths, sample_asset):
    """delete_asset_file entfernt Export-Einträge (z.B. GLTF)."""
    asset_path = asset_service.get_asset_dir(sample_asset)
    (asset_path / "export.gltf").write_bytes(b"{}")
    (asset_path / "export.bin").write_bytes(b"bin")
    asset_service.update_metadata_fields(
        sample_asset,
        {"exports": [{"output_file": "export.gltf", "format": "gltf"}]},
    )
    meta_before = asset_service.get_asset(sample_asset)
    assert len(meta_before.exports) == 1
    result = asset_service.delete_asset_file(sample_asset, "export.gltf")
    assert result is True
    assert not (asset_path / "export.gltf").exists()
    assert not (asset_path / "export.bin").exists()


def test_delete_asset_file_bin_also_removes_gltf(tmp_storage_paths, sample_asset):
    """delete_asset_file für .bin entfernt auch die zugehörige .gltf."""
    asset_path = asset_service.get_asset_dir(sample_asset)
    (asset_path / "model.gltf").write_bytes(b"{}")
    (asset_path / "model.bin").write_bytes(b"bin")
    asset_service.update_metadata_fields(
        sample_asset,
        {"exports": [{"output_file": "model.bin", "format": "gltf"}]},
    )
    result = asset_service.delete_asset_file(sample_asset, "model.bin")
    assert result is True
    assert not (asset_path / "model.bin").exists()
    assert not (asset_path / "model.gltf").exists()


def test_list_assets_sort_created_asc(tmp_storage_paths, tmp_assets_dir):
    """list_assets mit sort=created_asc sortiert älteste zuerst."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    assets = asset_service.list_assets(sort="created_asc")
    ids = [a.asset_id for a in assets if a.asset_id in (a1, a2)]
    assert len(ids) == 2


def test_get_file_path_returns_valid_path(tmp_storage_paths, sample_asset):
    """get_file_path gibt Pfad zurück wenn Datei existiert."""
    path = asset_service.get_file_path(sample_asset, "mesh.glb")
    assert path is not None
    assert path.exists()
    assert path.name == "mesh.glb"


def test_get_file_path_returns_none_for_missing_file(tmp_storage_paths, sample_asset):
    """get_file_path gibt None wenn Datei nicht existiert."""
    path = asset_service.get_file_path(sample_asset, "nonexistent.glb")
    assert path is None


def test_delete_asset_file_raises_when_file_not_found(tmp_storage_paths, sample_asset):
    """delete_asset_file wirft FileNotFoundError wenn Datei nicht im Asset existiert."""
    with pytest.raises(FileNotFoundError, match="nicht in Asset"):
        asset_service.delete_asset_file(sample_asset, "nonexistent.glb")


def test_delete_step_raises_when_asset_not_found(tmp_storage_paths):
    """delete_step wirft FileNotFoundError wenn Asset nicht existiert."""
    with pytest.raises(FileNotFoundError, match="nicht gefunden"):
        asset_service.delete_step("00000000-0000-0000-0000-000000000000", "mesh")


def test_delete_step_raises_for_invalid_step(tmp_storage_paths, sample_asset):
    """delete_step wirft ValueError für ungültigen Step-Namen."""
    with pytest.raises(ValueError, match="Ungültiger Step"):
        asset_service.delete_step(sample_asset, "invalid_step")


def test_delete_step_with_cascade(tmp_storage_paths, sample_asset):
    """delete_step mit cascade=True löscht auch abhängige Steps."""
    asset_path = asset_service.get_asset_dir(sample_asset)
    meta_path = asset_path / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["steps"]["image"] = {"file": "image_original.png", "provider_key": "upload"}
    meta["steps"]["bgremoval"] = {"file": "image_bgremoved.png", "provider_key": "rembg"}
    meta_path.write_text(json.dumps(meta, indent=2))
    (asset_path / "image_original.png").write_bytes(b"x")
    (asset_path / "image_bgremoved.png").write_bytes(b"x")

    result = asset_service.delete_step(sample_asset, "bgremoval", cascade=True)
    assert result.get("requires_confirmation") is False
    meta_after = asset_service.get_asset(sample_asset)
    assert "bgremoval" not in meta_after.steps
    assert "mesh" not in meta_after.steps


def test_get_dependent_steps():
    """get_dependent_steps gibt abhängige Steps zurück."""
    deps = asset_service.get_dependent_steps("image", {"bgremoval", "mesh"})
    assert "bgremoval" in deps
    assert "mesh" in deps
    deps2 = asset_service.get_dependent_steps("mesh", {"rigging"})
    assert "rigging" in deps2


def test_asset_metadata_to_dict_includes_optional_fields():
    """AssetMetadata.to_dict() enthält optionale Felder wenn gesetzt."""
    meta = asset_service.AssetMetadata(
        asset_id="test-id",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        steps={},
        sketchfab_upload={"uid": "abc"},
        source="sketchfab",
        sketchfab_uid="uid123",
        sketchfab_url="https://sketchfab.com/...",
        sketchfab_author="author",
        downloaded_at="2025-01-01T00:00:00Z",
        deleted_at="2025-01-01T00:00:00Z",
        name="Test",
        tags=["a", "b"],
        rating=5,
        notes="Notes",
        favorited=True,
    )
    d = meta.to_dict()
    assert d["sketchfab_upload"] == {"uid": "abc"}
    assert d["source"] == "sketchfab"
    assert d["sketchfab_uid"] == "uid123"
    assert d["sketchfab_url"] == "https://sketchfab.com/..."
    assert d["sketchfab_author"] == "author"
    assert d["downloaded_at"] == "2025-01-01T00:00:00Z"
    assert d["deleted_at"] == "2025-01-01T00:00:00Z"
    assert d["name"] == "Test"
    assert d["tags"] == ["a", "b"]
    assert d["rating"] == 5
    assert d["notes"] == "Notes"
    assert d["favorited"] is True


def test_list_assets_filter_source(tmp_storage_paths, tmp_assets_dir):
    """list_assets filtert nach source."""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, steps={})
    _create_asset_with_meta(tmp_assets_dir, a2, steps={})
    asset_service.update_metadata_fields(a1, {"source": "sketchfab"})
    asset_service.update_metadata_fields(a2, {"source": "upload"})

    assets = asset_service.list_assets(source="sketchfab")
    assert any(a.asset_id == a1 for a in assets)
    assert not any(a.asset_id == a2 for a in assets)


def test_restore_asset_already_active(tmp_storage_paths, tmp_assets_dir):
    """restore_asset bei nicht-gelöschtem Asset gibt True zurück."""
    a1 = str(uuid.uuid4())
    _create_asset_with_meta(tmp_assets_dir, a1, deleted=False)
    result = asset_service.restore_asset(a1)
    assert result is True
