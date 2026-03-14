"""Unit-Tests für UniRigProvider mit respx/httpx-Mocks."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from app.providers.rigging.unirig_provider import UniRigProvider
from app.providers.rigging.base import RiggingParams, RiggingResult


@pytest.fixture
def minimal_glb_bytes() -> bytes:
    """Minimales GLB für Tests (trimesh-kompatibel)."""
    import io

    import numpy as np
    import trimesh

    verts = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=np.float32)
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    bio = io.BytesIO()
    mesh.export(file_obj=bio, file_type="glb")
    return bio.getvalue()


@respx.mock
@pytest.mark.asyncio
async def test_unirig_success(minimal_glb_bytes: bytes, monkeypatch):
    """UniRig Provider: Erfolgreiches Rigging mit gemockten HTTP-Calls."""
    monkeypatch.setenv("HF_TOKEN", "hf-test-token")
    glb_url = "https://example.com/source.glb"

    respx.get(glb_url).mock(return_value=httpx.Response(200, content=minimal_glb_bytes))

    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
        f.write(minimal_glb_bytes)
        out_path = f.name

    try:
        with (
            patch("app.providers.rigging.unirig_provider.Client"),
            patch.object(
                UniRigProvider,
                "_run_predict",
                return_value=out_path,
            ),
        ):
            provider = UniRigProvider()
            result = await provider.rig(
                RiggingParams(source_glb_url=glb_url, asset_id=None)
            )
            assert isinstance(result, RiggingResult)
            assert result.provider_key == "unirig"
            assert len(result.rigged_glb_bytes) > 0
    finally:
        Path(out_path).unlink(missing_ok=True)


@respx.mock
@pytest.mark.asyncio
async def test_unirig_timeout(monkeypatch):
    """UniRig Provider: Timeout bei predict."""
    import asyncio

    monkeypatch.setenv("HF_TOKEN", "hf-test-token")
    glb_url = "https://example.com/source.glb"
    respx.get(glb_url).mock(return_value=httpx.Response(200, content=b"glb"))

    from app.exceptions import UniRigTimeoutError

    async def raise_timeout(*args, **kwargs):
        raise asyncio.TimeoutError()

    with (
        patch("app.providers.rigging.unirig_provider.Client"),
        patch(
            "app.providers.rigging.unirig_provider.asyncio.wait_for",
            side_effect=raise_timeout,
        ),
    ):
        provider = UniRigProvider()
        with pytest.raises(UniRigTimeoutError):
            await provider.rig(
                RiggingParams(source_glb_url=glb_url, asset_id=None)
            )
