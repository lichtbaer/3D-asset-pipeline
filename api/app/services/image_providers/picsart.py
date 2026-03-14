"""PicsArt GenAI Hub Image-Provider."""

import asyncio
import logging
import os
from typing import Any

import httpx

from app.services.image_providers.base import ImageProvider

logger = logging.getLogger(__name__)

PICSART_BASE_URL = "https://genai-api.picsart.io/v1"
POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 60

# AIR-URNs aus docs.picsart.io/docs/ai-providers-hub-introduction
PICSART_AIR_URNS: dict[str, str | None] = {
    "picsart-default": None,
    "picsart-flux-dev": "urn:air:sdxl:model:fluxai:flux_kontext_pro@1",
    "picsart-flux-max": "urn:air:sdxl:model:fluxai:flux_kontext_max@1",
    "picsart-dalle3": "urn:air:openai:model:openai:dall-e-3@1",
    "picsart-ideogram": "urn:air:ideogram:model:ideogram:ideogram-2a@1",
}

DEFAULT_PARAM_SCHEMA = {
    "type": "object",
    "properties": {
        "width": {"type": "integer", "default": 1024, "minimum": 256, "maximum": 2048},
        "height": {"type": "integer", "default": 1024, "minimum": 256, "maximum": 2048},
        "negative_prompt": {"type": ["string", "null"], "default": None},
        "count": {"type": "integer", "default": 1, "minimum": 1, "maximum": 4},
    },
    "required": ["width", "height"],
}


def create_picsart_providers() -> list["PicsArtImageProvider"]:
    """Erstellt alle konfigurierten PicsArt-Provider-Instanzen."""
    display_names = {
        "picsart-default": "PicsArt Default",
        "picsart-flux-dev": "PicsArt Flux Dev",
        "picsart-flux-max": "PicsArt Flux Max",
        "picsart-dalle3": "PicsArt DALL-E 3",
        "picsart-ideogram": "PicsArt Ideogram 2A",
    }
    return [
        PicsArtImageProvider(key, display_names[key], air_urn)
        for key, air_urn in PICSART_AIR_URNS.items()
    ]


class PicsArtImageProvider(ImageProvider):
    """PicsArt GenAI Hub Provider — ein Objekt pro konfiguriertem Modell."""

    def __init__(
        self,
        provider_key: str,
        display_name: str,
        air_urn: str | None,
    ):
        self.provider_key = provider_key
        self.display_name = display_name
        self.air_urn = air_urn

    def default_params(self) -> dict[str, Any]:
        return {
            "width": 1024,
            "height": 1024,
            "negative_prompt": None,
            "count": 1,
        }

    def param_schema(self) -> dict[str, Any]:
        return DEFAULT_PARAM_SCHEMA.copy()

    async def generate(self, prompt: str, params: dict[str, Any]) -> str:
        """
        Führt die Bildgenerierung via PicsArt API aus.
        Gibt die URL des generierten Bildes zurück.

        Raises:
            RuntimeError: Bei API-Fehlern oder Timeout
        """
        api_key = os.getenv("PICSART_API_KEY")
        if not api_key:
            raise RuntimeError("PICSART_API_KEY nicht konfiguriert")

        width = params.get("width", 1024)
        height = params.get("height", 1024)
        negative_prompt = params.get("negative_prompt")
        count = params.get("count", 1)

        request_body: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "count": count,
        }
        if negative_prompt:
            request_body["negative_prompt"] = negative_prompt
        if self.air_urn is not None:
            request_body["model"] = self.air_urn

        headers = {
            "X-Picsart-API-Key": api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PICSART_BASE_URL}/text2image",
                headers=headers,
                json=request_body,
            )

            if response.status_code != 202:
                error_detail = response.text
                try:
                    err_json = response.json()
                    error_detail = err_json.get("message", str(err_json))
                except Exception:
                    pass
                raise RuntimeError(
                    f"PicsArt API Fehler ({response.status_code}): {error_detail}"
                )

            data = response.json()
            transaction_id = (
                data.get("transaction_id")
                or data.get("inference_id")
                or data.get("id")
            )
            if not transaction_id:
                raise RuntimeError(
                    f"PicsArt API: Keine transaction_id in Response: {data}"
                )

            result_url = await _poll_for_result(
                client, headers, transaction_id
            )
            if result_url:
                return result_url
            raise RuntimeError(
                f"Timeout nach {POLL_TIMEOUT_SEC}s – Bildgenerierung nicht abgeschlossen"
            )


async def _poll_for_result(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    transaction_id: str,
) -> str | None:
    """Pollt alle 2s, max 60s. Gibt result_url zurück oder None bei Fehler."""
    poll_url = f"{PICSART_BASE_URL}/text2image/{transaction_id}"
    alt_poll_url = f"{PICSART_BASE_URL}/text2image/inferences/{transaction_id}"

    elapsed = 0
    while elapsed < POLL_TIMEOUT_SEC:
        await asyncio.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC

        try:
            response = await client.get(poll_url, headers=headers)
            if response.status_code == 404:
                response = await client.get(alt_poll_url, headers=headers)
        except httpx.RequestError as e:
            raise RuntimeError(f"Poll Request-Fehler: {e}")

        # 202 = noch in Bearbeitung, weiter pollen; 200 = Ergebnis da
        if response.status_code not in (200, 202):
            raise RuntimeError(
                f"Poll-Fehler ({response.status_code}): {response.text}"
            )

        data = response.json()
        status = (data.get("status") or "").lower()

        if status in ("done", "completed", "success"):
            url = _extract_result_url(data)
            if url:
                return url
            raise RuntimeError(
                "PicsArt: Keine result_url in fertiger Response"
            )

        if status in ("failed", "error"):
            raise RuntimeError(
                data.get("message", data.get("error", "Unbekannter Fehler"))
            )

        # 202 oder status "processing" → weiter warten

    return None


def _extract_result_url(data: dict[str, Any]) -> str | None:
    """Extrahiert die Bild-URL aus der PicsArt-Response."""
    if "result_url" in data and data["result_url"]:
        return str(data["result_url"])
    if "url" in data and data["url"]:
        return str(data["url"])
    if "image_url" in data and data["image_url"]:
        return str(data["image_url"])
    # PicsArt GenAI: {"data": [{"id": "...", "url": "..."}], "status": "success"}
    if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
        item = data["data"][0]
        if isinstance(item, dict):
            u = item.get("url") or item.get("result_url") or item.get("image_url")
            if u:
                return str(u)
        if isinstance(item, str):
            return item
    if "images" in data and isinstance(data["images"], list) and len(data["images"]) > 0:
        img = data["images"][0]
        if isinstance(img, str):
            return img
        if isinstance(img, dict):
            return img.get("url") or img.get("result_url") or img.get("image_url")
    return None
