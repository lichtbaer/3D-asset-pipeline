"""
Unit-Tests für mesh_processing_service.
Kritisch: simplify/repair/clip_floor überschreiben nie das Original mesh.glb.
"""

import pytest

from app.services import mesh_processing_service
from app.schemas.mesh_processing import RepairOperation


def test_simplify_does_not_overwrite_original(sample_asset: str, tmp_storage_paths):
    """
    Nicht-destruktiv: Original mesh.glb wird nie überschrieben.
    simplify speichert mesh_simplified_{target_faces}.glb.
    """
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    original_path = asset_dir / "mesh.glb"
    original_content = original_path.read_bytes()
    original_size = len(original_content)

    output_file, _ = mesh_processing_service.simplify(
        sample_asset, "mesh.glb", target_faces=2
    )

    # Original unverändert
    assert original_path.exists()
    assert original_path.read_bytes() == original_content
    assert len(original_path.read_bytes()) == original_size

    # Output ist neue Datei
    assert output_file == "mesh_simplified_2.glb"
    output_path = asset_dir / output_file
    assert output_path.exists()
    assert output_path != original_path


def test_analyze_returns_mesh_analysis(sample_asset: str, tmp_storage_paths):
    """Analyze liefert MeshAnalysis mit vertex_count, face_count, etc."""
    result = mesh_processing_service.analyze(sample_asset, "mesh.glb")
    assert result.vertex_count >= 3
    assert result.face_count >= 1
    assert "min_x" in result.bounding_box
    assert result.file_size_bytes > 0


def test_repair_does_not_overwrite_original(sample_asset: str, tmp_storage_paths):
    """Repair speichert mesh_repaired.glb, Original bleibt unverändert."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    original_path = asset_dir / "mesh.glb"
    original_content = original_path.read_bytes()

    output_file, _ = mesh_processing_service.repair(
        sample_asset, "mesh.glb", [RepairOperation.REMOVE_DUPLICATES]
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "mesh_repaired.glb"
    assert (asset_dir / output_file).exists()


def test_clip_floor_creates_new_file(sample_asset: str, tmp_storage_paths):
    """clip_floor speichert mesh_clipped.glb, Original bleibt."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    original_path = asset_dir / "mesh.glb"
    original_content = original_path.read_bytes()

    output_file, result = mesh_processing_service.clip_floor(
        sample_asset, "mesh.glb", y_threshold=0.5
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "mesh_clipped.glb"
    assert (asset_dir / output_file).exists()


def test_remove_small_components_creates_new_file(sample_asset: str, tmp_storage_paths):
    """remove_small_components speichert mesh_cleaned.glb."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    original_path = asset_dir / "mesh.glb"
    original_content = original_path.read_bytes()

    output_file, _ = mesh_processing_service.remove_small_components(
        sample_asset, "mesh.glb", min_component_ratio=0.05
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "mesh_cleaned.glb"
    assert (asset_dir / output_file).exists()
