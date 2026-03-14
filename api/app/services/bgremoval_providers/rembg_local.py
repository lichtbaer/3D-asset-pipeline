"""rembg lokaler Provider — läuft im Container, keine externe API."""

import asyncio
import logging
import os
import tempfile
from typing import Any

import httpx

from app.config.storage import BGREMOVAL_STORAGE_PATH
from app.services.bgremoval_providers.base import BgRemovalProvider

logger = logging.getLogger(__name__)

PARAM_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}


class RembgLocalProvider(BgRemovalProvider):
    """rembg (lokal) — Python-Library, U2Net-Modell, keine externen Credits."""

    provider_key = "rembg-local"
    display_name = "rembg (lokal)"

    def param_schema(self) -> dict[str, Any]:
        return PARAM_SCHEMA.copy()

    async def remove_background(
        self, image_url: str, *, job_id: str | None = None
    ) -> str:
        """
        Lädt Bild herunter, entfernt Hintergrund mit rembg, speichert lokal.
        Gibt URL /static/bgremoval/{job_id}.png zurück.
        """
        if not job_id:
            raise RuntimeError("rembg-local benötigt job_id für Speicherpfad")

        # 1. Bild herunterladen
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_bytes = response.content

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            temp_input = f.name

        try:
            # 2. rembg.remove (blockierend) in Thread ausführen
            output_bytes = await asyncio.to_thread(
                self._run_rembg, temp_input
            )

            # 3. Output speichern
            BGREMOVAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
            output_path = BGREMOVAL_STORAGE_PATH / f"{job_id}.png"
            output_path.write_bytes(output_bytes)

            # 4. Statische URL zurückgeben
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            return f"{base_url.rstrip('/')}/static/bgremoval/{job_id}.png"
        finally:
            if os.path.exists(temp_input):
                try:
                    os.unlink(temp_input)
                except OSError:
                    pass

    def _run_rembg(self, input_path: str) -> bytes:
        """Synchroner rembg-Aufruf (blockiert)."""
        from rembg import remove

        with open(input_path, "rb") as f:
            input_data = f.read()
        output_data = remove(input_data)
        return bytes(output_data)
