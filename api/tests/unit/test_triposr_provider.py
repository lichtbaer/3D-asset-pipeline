"""Unit-Tests für TripoSRProvider mit Mock."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.mesh_providers.triposr import TripoSRProvider


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    """Minimales PNG."""
    png = tmp_path / "test.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    return png


@pytest.mark.asyncio
async def test_triposr_success(image_path: Path, monkeypatch):
    """TripoSR Provider: Erfolgreiche Generierung."""
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    out_glb = str(image_path.with_suffix(".glb"))
    Path(out_glb).write_bytes(b"glb")

    with patch.object(TripoSRProvider, "_run_predict", return_value=out_glb):
        provider = TripoSRProvider()
        result = await provider.generate(str(image_path), {})
        assert result.endswith(".glb")
