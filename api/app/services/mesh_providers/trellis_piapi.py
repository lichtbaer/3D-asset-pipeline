"""
TRELLIS Mesh-Provider via PiAPI REST-API.
Pay-as-you-go, async: Submit → Poll → Download GLB.
Nur registriert wenn PIAPI_API_KEY gesetzt ist.
"""
import asyncio
import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from app.services.mesh_providers.base import MeshProvider

logger = logging.getLogger(__name__)

PIAPI_BASE_URL = "https://api.piapi.ai/api/v1"
PIAPI_MODEL = "Qubico/trellis2"
PIAPI_TASK_TYPE = "image-to-3d"
POLL_INTERVAL_SEC = 2
MAX_POLL_ATTEMPTS = 180  # ~6 min bei 2s Intervall
MESH_TIMEOUT_SEC = 400


class TrellisPiAPIProvider(MeshProvider):
    provider_key = "trellis-piapi"
    display_name = "TRELLIS (PiAPI)"

    def default_params(self) -> dict[str, Any]:
        return {
            "seed": 0,
        }

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "seed": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 2147483647,
                    "default": 0,
                    "description": "Random Seed für Reproduzierbarkeit",
                },
            },
            "required": [],
        }

    def _image_to_base64(self, image_path: str) -> str:
        """Liest Bild und gibt Base64-String zurück."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")

    async def generate(self, image_path: str, params: dict[str, Any]) -> str:
        api_key = _get_piapi_api_key()
        merged = {**self.default_params(), **params}
        seed = merged.get("seed", 0)

        image_b64 = self._image_to_base64(image_path)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Task starten
            create_resp = await client.post(
                f"{PIAPI_BASE_URL}/task",
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "model": PIAPI_MODEL,
                    "task_type": PIAPI_TASK_TYPE,
                    "input": {
                        "image": f"data:image/png;base64,{image_b64}",
                        "seed": seed,
                    },
                },
            )

            if create_resp.status_code == 401:
                _log_and_raise(
                    "PiAPI: Ungültiger oder fehlender API-Key",
                    "PiAPIAuthError",
                )
            if create_resp.status_code == 402:
                _log_and_raise(
                    "PiAPI: Unzureichende Credits (insufficient credits)",
                    "PiAPIInsufficientCreditsError",
                )
            if create_resp.status_code == 429:
                _log_and_raise(
                    "PiAPI: Rate Limit überschritten",
                    "PiAPIRateLimitError",
                )
            create_resp.raise_for_status()

            data = create_resp.json()
            task_id = data.get("task_id") or data.get("data", {}).get("task_id")
            if not task_id:
                _log_and_raise(
                    f"PiAPI: Keine task_id in Response: {data}",
                    "PiAPIInvalidResponseError",
                )

            # 2. Polling
            for attempt in range(MAX_POLL_ATTEMPTS):
                await asyncio.sleep(POLL_INTERVAL_SEC)

                poll_resp = await client.get(
                    f"{PIAPI_BASE_URL}/task/{task_id}",
                    headers={"x-api-key": api_key},
                )
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()

                # Response kann data-wrapper haben
                inner = poll_data.get("data", poll_data)
                status = (inner.get("status") or "").lower()

                if status in ("success", "completed", "done"):
                    break
                if status == "failed":
                    err_msg = inner.get("error", inner.get("message", "Task failed"))
                    _log_and_raise(
                        f"PiAPI Task fehlgeschlagen: {err_msg}",
                        "PiAPITaskFailedError",
                    )

                if attempt >= MAX_POLL_ATTEMPTS - 1:
                    _log_and_raise(
                        f"PiAPI: Timeout nach {MAX_POLL_ATTEMPTS} Poll-Versuchen",
                        "PiAPITimeoutError",
                    )

            # 3. GLB-URL aus Output extrahieren
            output = inner.get("output") or inner
            if isinstance(output, dict):
                glb_url = (
                    output.get("glb_url")
                    or output.get("output_url")
                    or output.get("url")
                    or output.get("glb")
                )
            else:
                glb_url = str(output) if output else None

            if not glb_url:
                _log_and_raise(
                    f"PiAPI: Keine GLB-URL in Output: {inner}",
                    "PiAPIInvalidResponseError",
                )

            # 4. GLB herunterladen
            dl_resp = await client.get(str(glb_url))
            dl_resp.raise_for_status()
            glb_bytes = dl_resp.content

        # 5. In temporäre Datei schreiben und Pfad zurückgeben
        glb_path = str(Path(image_path).with_suffix(".glb"))
        Path(glb_path).write_bytes(glb_bytes)
        return glb_path


def _get_piapi_api_key() -> str:
    key = os.getenv("PIAPI_API_KEY", "").strip()
    if not key:
        raise ValueError("PIAPI_API_KEY nicht konfiguriert")
    return key


def _log_and_raise(message: str, error_type: str) -> None:
    logger.error(
        message,
        extra={
            "error_type": error_type,
            "provider_key": TrellisPiAPIProvider.provider_key,
        },
    )
    raise RuntimeError(message)
