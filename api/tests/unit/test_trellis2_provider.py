"""Unit-Tests für Trellis2Provider mit Mock (gradio_client)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.exceptions import Trellis2InvalidImageError, Trellis2TimeoutError
from app.services.mesh_providers.trellis2 import Trellis2Provider


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    """Minimales PNG für Tests."""
    png = tmp_path / "test.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return png


@pytest.mark.asyncio
async def test_trellis2_success(image_path: Path, monkeypatch):
    """Trellis2 Provider: Erfolgreiche Generierung."""
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    out_glb = str(image_path.with_suffix(".glb"))
    Path(out_glb).write_bytes(b"glb-content")

    with patch.object(
        Trellis2Provider,
        "_run_predict",
        return_value=out_glb,
    ):
        provider = Trellis2Provider()
        result = await provider.generate(str(image_path), {})
        assert result.endswith(".glb")
        assert Path(result).exists()


@pytest.mark.asyncio
async def test_trellis2_timeout(image_path: Path, monkeypatch):
    """Trellis2 Provider: Timeout."""
    import asyncio

    monkeypatch.setenv("HF_TOKEN", "hf-test")

    with patch(
        "app.services.mesh_providers.trellis2.asyncio.wait_for",
        side_effect=asyncio.TimeoutError(),
    ):
        provider = Trellis2Provider()
        with pytest.raises(Trellis2TimeoutError):
            await provider.generate(str(image_path), {})


@pytest.mark.asyncio
async def test_trellis2_invalid_image(image_path: Path, monkeypatch):
    """Trellis2 Provider: Ungültiges Bild liefert keine GLB."""
    monkeypatch.setenv("HF_TOKEN", "hf-test")

    with patch.object(Trellis2Provider, "_run_predict", return_value=None):
        provider = Trellis2Provider()
        with pytest.raises(Trellis2InvalidImageError):
            await provider.generate(str(image_path), {})
