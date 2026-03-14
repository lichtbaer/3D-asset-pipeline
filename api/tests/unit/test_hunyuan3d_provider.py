"""Unit-Tests für Hunyuan3DProvider mit Mock."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.mesh_providers.hunyuan3d import Hunyuan3DProvider


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    """Minimales PNG."""
    png = tmp_path / "test.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    return png


@pytest.mark.asyncio
async def test_hunyuan3d_success(image_path: Path, monkeypatch):
    """Hunyuan3D Provider: Erfolgreiche Generierung."""
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    out_glb = str(image_path.with_suffix(".glb"))
    Path(out_glb).write_bytes(b"glb")

    with patch.object(Hunyuan3DProvider, "_run_predict", return_value=out_glb):
        provider = Hunyuan3DProvider()
        result = await provider.generate(str(image_path), {})
        assert result.endswith(".glb")


@pytest.mark.asyncio
async def test_hunyuan3d_no_glb(image_path: Path, monkeypatch):
    """Hunyuan3D Provider: Keine GLB zurück."""
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    with patch.object(Hunyuan3DProvider, "_run_predict", return_value=None):
        provider = Hunyuan3DProvider()
        with pytest.raises(RuntimeError, match="keine GLB"):
            await provider.generate(str(image_path), {})
