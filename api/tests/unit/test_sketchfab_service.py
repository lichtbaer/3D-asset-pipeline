"""Unit-Tests für SketchfabService mit respx-Mocks."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from app.services.sketchfab_service import (
    SketchfabService,
    SketchfabUploadResult,
    _extract_uid,
)


def test_extract_uid_direct():
    """_extract_uid: Direkte UID wird erkannt."""
    assert _extract_uid("abc12345") == "abc12345"
    assert _extract_uid("  xyz98765  ") == "xyz98765"


def test_extract_uid_from_url():
    """_extract_uid: UID aus Sketchfab-URL extrahieren."""
    assert (
        _extract_uid("https://sketchfab.com/3d-models/chair-abc12345")
        == "abc12345"
    )
    assert (
        _extract_uid("https://sketchfab.com/models/abc12345")
        == "abc12345"
    )


def test_extract_uid_invalid():
    """_extract_uid: Ungültige Eingabe."""
    assert _extract_uid("https://other.com/page") is None
    assert _extract_uid("short") is None


@respx.mock
@pytest.mark.asyncio
async def test_list_my_models_success():
    """SketchfabService.list_my_models: Erfolgreiche Abfrage."""
    respx.get("https://api.sketchfab.com/v3/me/models").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "uid": "uid1",
                        "name": "Model 1",
                        "viewerUrl": "https://sketchfab.com/3d-models/uid1",
                        "thumbnails": {"images": [{"url": "https://thumb1", "width": 200}]},
                        "vertexCount": 100,
                        "faceCount": 50,
                        "isDownloadable": True,
                        "createdAt": "2025-01-01",
                    }
                ]
            },
        )
    )

    svc = SketchfabService(api_token="test-token")
    models = await svc.list_my_models()
    assert len(models) == 1
    assert models[0]["uid"] == "uid1"
    assert models[0]["name"] == "Model 1"
    assert models[0]["thumbnail_url"] == "https://thumb1"


@respx.mock
@pytest.mark.asyncio
async def test_list_my_models_api_error():
    """SketchfabService.list_my_models: API-Fehler."""
    respx.get("https://api.sketchfab.com/v3/me/models").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    svc = SketchfabService(api_token="test-token")
    with pytest.raises(RuntimeError, match="fehlgeschlagen"):
        await svc.list_my_models()


@respx.mock
@pytest.mark.asyncio
async def test_download_model_404():
    """SketchfabService.download_model: Modell nicht gefunden."""
    respx.get("https://api.sketchfab.com/v3/models/abc12345/download").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )

    svc = SketchfabService(api_token="test-token")
    with pytest.raises(RuntimeError, match="nicht gefunden"):
        await svc.download_model("abc12345")


@respx.mock
@pytest.mark.asyncio
async def test_download_model_403_not_downloadable():
    """SketchfabService.download_model: Modell nicht zum Download freigegeben."""
    respx.get("https://api.sketchfab.com/v3/models/abc12345/download").mock(
        return_value=httpx.Response(403, json={"detail": "Forbidden"})
    )

    svc = SketchfabService(api_token="test-token")
    with pytest.raises(RuntimeError, match="nicht zum Download freigegeben"):
        await svc.download_model("abc12345")
