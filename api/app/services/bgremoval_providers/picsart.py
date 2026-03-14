"""PicsArt Remove Background API Provider."""

import logging
import os
from typing import Any

import httpx

from app.services.bgremoval_providers.base import BgRemovalProvider

logger = logging.getLogger(__name__)

PICSART_REMOVEBG_URL = "https://api.picsart.io/tools/1.0/removebg"

# Minimales Schema – PicsArt RemoveBG hat keine zusätzlichen Parameter
PARAM_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}


class PicsArtBgRemovalProvider(BgRemovalProvider):
    """PicsArt Remove Background API — 8 Credits pro Call."""

    provider_key = "picsart"
    display_name = "PicsArt Remove Background"

    def param_schema(self) -> dict[str, Any]:
        return PARAM_SCHEMA.copy()

    async def remove_background(
        self, image_url: str, *, job_id: str | None = None
    ) -> str:
        """
        Ruft die PicsArt Remove Background API auf.

        Raises:
            RuntimeError: Bei API-Fehlern, 401/403 mit klarer Fehlermeldung
        """
        api_key = os.getenv("PICSART_API_KEY")
        if not api_key:
            raise RuntimeError(
                "PicsArt API-Zugang nicht verfügbar — PICSART_API_KEY nicht konfiguriert. "
                "Bitte anderen Provider konfigurieren oder API-Key setzen."
            )

        headers = {
            "X-Picsart-API-Key": api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }
        body = {
            "image_url": image_url,
            "output_type": "cutout",
            "format": "PNG",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                PICSART_REMOVEBG_URL,
                headers=headers,
                json=body,
            )

            if response.status_code in (401, 403):
                raise RuntimeError(
                    "PicsArt API-Zugang nicht verfügbar — API-Key ungültig oder "
                    "Credits erschöpft. Bitte anderen Provider konfigurieren."
                )

            if response.status_code != 200:
                error_detail = response.text
                try:
                    err_json = response.json()
                    error_detail = err_json.get("message", err_json.get("error", str(err_json)))
                except Exception:
                    pass
                raise RuntimeError(
                    f"PicsArt Remove Background Fehler ({response.status_code}): {error_detail}"
                )

            data = response.json()
            # PicsArt: {"image": {"url": "..."}, "metadata": {...}}
            result_url = (
                data.get("image", {}).get("url")
                or data.get("data", {}).get("url")
                or data.get("url")
                or data.get("result_url")
                or data.get("image_url")
            )
            if not result_url:
                raise RuntimeError(
                    "PicsArt Remove Background: Keine result_url in Response"
                )
            return str(result_url)
