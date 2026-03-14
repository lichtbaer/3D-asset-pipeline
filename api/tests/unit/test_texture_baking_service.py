"""Unit-Tests für TextureBakingService mit subprocess-Mock."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import (
    BlenderNotAvailableError,
    TextureBakingError,
    TextureBakingTimeoutError,
)
from app.services.texture_baking_service import (
    TextureBakingService,
    _check_blender_available,
    _target_stem_to_output_filename,
)


def test_target_stem_to_output_filename():
    """Output-Dateiname aus Target-Stem."""
    assert (
        _target_stem_to_output_filename("mesh_simplified_10000.glb")
        == "mesh_baked_mesh_simplified_10000.glb"
    )
    assert (
        _target_stem_to_output_filename("mesh.glb")
        == "mesh_baked_mesh.glb"
    )


def test_check_blender_available_false():
    """Blender nicht verfügbar."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()
        assert _check_blender_available() is False


def test_check_blender_available_true():
    """Blender verfügbar."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert _check_blender_available() is True


def test_bake_raises_when_blender_unavailable(tmp_storage_paths, sample_asset):
    """TextureBakingService.bake: Blender nicht verfügbar."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    (asset_dir / "mesh.glb").write_bytes(b"glb")
    (asset_dir / "mesh_simplified.glb").write_bytes(b"glb")

    with patch(
        "app.services.texture_baking_service._check_blender_available",
        return_value=False,
    ):
        svc = TextureBakingService()
        with pytest.raises(BlenderNotAvailableError):
            svc.bake(
                sample_asset,
                "mesh.glb",
                "mesh_simplified.glb",
            )


def test_bake_subprocess_called(tmp_storage_paths, sample_asset):
    """TextureBakingService.bake: subprocess.run wird aufgerufen."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    (asset_dir / "mesh.glb").write_bytes(b"glb")
    (asset_dir / "mesh_simplified.glb").write_bytes(b"glb")
    output_path = asset_dir / "mesh_baked_mesh_simplified.glb"
    output_path.write_bytes(b"baked")

    fake_script = tmp_storage_paths.parent / "fake_script.py"
    fake_script.write_text("# fake")

    with (
        patch(
            "app.services.texture_baking_service._check_blender_available",
            return_value=True,
        ),
        patch(
            "app.services.texture_baking_service._get_script_path",
            return_value=fake_script,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        svc = TextureBakingService()
        result = svc.bake(
            sample_asset,
            "mesh.glb",
            "mesh_simplified.glb",
        )
        assert mock_run.called
        assert result == "mesh_baked_mesh_simplified.glb"


def test_bake_timeout(tmp_storage_paths, sample_asset):
    """TextureBakingService.bake: Timeout führt zu TextureBakingTimeoutError."""
    import subprocess

    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset)
    (asset_dir / "mesh.glb").write_bytes(b"glb")
    (asset_dir / "mesh_simplified.glb").write_bytes(b"glb")
    fake_script = tmp_storage_paths.parent / "fake_script_timeout.py"
    fake_script.write_text("# fake")

    with (
        patch(
            "app.services.texture_baking_service._check_blender_available",
            return_value=True,
        ),
        patch(
            "app.services.texture_baking_service._get_script_path",
            return_value=fake_script,
        ),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)),
    ):
        svc = TextureBakingService()
        with pytest.raises(TextureBakingTimeoutError):
            svc.bake(
                sample_asset,
                "mesh.glb",
                "mesh_simplified.glb",
            )
