"""Unit-Tests für TrellisPiAPIProvider mit respx-Mocks."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.services.mesh_providers.trellis_piapi import (
    PIAPI_BASE_URL,
    TrellisPiAPIProvider,
)


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    """Minimales PNG für Tests."""
    png = tmp_path / "test.png"
    # Minimal valid PNG header
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return png


@respx.mock
@pytest.mark.asyncio
async def test_trellis_piapi_success(image_path: Path, monkeypatch):
    """PiAPI Provider: Erfolgreiche Generierung mit gemockten HTTP-Calls."""
    monkeypatch.setenv("PIAPI_API_KEY", "test-key")

    # 1. Task erstellen
    respx.post(f"{PIAPI_BASE_URL}/task").mock(
        return_value=httpx.Response(200, json={"task_id": "task-123"})
    )
    # 2. Poll: success
    respx.get(f"{PIAPI_BASE_URL}/task/task-123").mock(
        return_value=httpx.Response(
            200,
            json={"status": "success", "output": {"glb_url": "https://example.com/out.glb"}},
        )
    )
    # 3. GLB-Download
    glb_bytes = b"glb-binary-content"
    respx.get("https://example.com/out.glb").mock(
        return_value=httpx.Response(200, content=glb_bytes)
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        provider = TrellisPiAPIProvider()
        result = await provider.generate(str(image_path), {})
        assert result.endswith(".glb")
        assert Path(result).exists()
        assert Path(result).read_bytes() == glb_bytes


@respx.mock
@pytest.mark.asyncio
async def test_trellis_piapi_401_raises(image_path: Path, monkeypatch):
    """PiAPI Provider: 401 führt zu RuntimeError."""
    monkeypatch.setenv("PIAPI_API_KEY", "test-key")
    respx.post(f"{PIAPI_BASE_URL}/task").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )

    with pytest.raises(RuntimeError, match="API-Key"):
        provider = TrellisPiAPIProvider()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await provider.generate(str(image_path), {})


@respx.mock
@pytest.mark.asyncio
async def test_trellis_piapi_timeout(image_path: Path, monkeypatch):
    """PiAPI Provider: Timeout beim Polling."""
    monkeypatch.setenv("PIAPI_API_KEY", "test-key")
    respx.post(f"{PIAPI_BASE_URL}/task").mock(
        return_value=httpx.Response(200, json={"task_id": "task-123"})
    )
    respx.get(f"{PIAPI_BASE_URL}/task/task-123").mock(
        return_value=httpx.Response(200, json={"status": "pending"})
    )

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch(
            "app.services.mesh_providers.trellis_piapi.MAX_POLL_ATTEMPTS",
            2,
        ),
    ):
        provider = TrellisPiAPIProvider()
        with pytest.raises(RuntimeError, match="Timeout"):
            await provider.generate(str(image_path), {})
