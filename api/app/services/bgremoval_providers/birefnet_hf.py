"""BiRefNet via Hugging Face Space — stärkeres Modell, gradio_client."""

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx

from app.config.storage import BGREMOVAL_STORAGE_PATH
from app.services.bgremoval_providers.base import BgRemovalProvider

logger = logging.getLogger(__name__)

# not-lain/background-removal: BiRefNet-basiert, einfache API
BIREFNET_SPACE = "not-lain/background-removal"
BIREFNET_TIMEOUT_SEC = 120

PARAM_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}


class BiRefNetHfProvider(BgRemovalProvider):
    """BiRefNet (HF Space) — stärkeres Modell via gradio_client."""

    provider_key = "birefnet-hf"
    display_name = "BiRefNet (HF Space)"

    def param_schema(self) -> dict[str, Any]:
        return PARAM_SCHEMA.copy()

    async def remove_background(
        self, image_url: str, *, job_id: str | None = None
    ) -> str:
        """
        Lädt Bild, ruft BiRefNet HF Space auf, speichert Output lokal.
        Gibt URL /static/bgremoval/{job_id}.png zurück.
        """
        if not job_id:
            raise RuntimeError("birefnet-hf benötigt job_id für Speicherpfad")

        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise RuntimeError(
                "BiRefNet HF Space benötigt HF_TOKEN — bitte konfigurieren."
            )

        # 1. Bild herunterladen
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_bytes = response.content

        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as f:
            f.write(image_bytes)
            temp_input = f.name

        try:
            # 2. gradio_client predict (blockierend) in Thread
            result_path = await asyncio.wait_for(
                asyncio.to_thread(
                    self._run_predict, temp_input, hf_token
                ),
                timeout=BIREFNET_TIMEOUT_SEC,
            )

            if not result_path or not Path(result_path).exists():
                raise RuntimeError(
                    "BiRefNet HF Space lieferte kein Ergebnis"
                )

            # 3. Nach Storage kopieren
            BGREMOVAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
            output_path = BGREMOVAL_STORAGE_PATH / f"{job_id}.png"
            shutil.copy2(result_path, output_path)

            # 4. Statische URL
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            return f"{base_url.rstrip('/')}/static/bgremoval/{job_id}.png"
        finally:
            if os.path.exists(temp_input):
                try:
                    os.unlink(temp_input)
                except OSError:
                    pass

    def _run_predict(self, image_path: str, hf_token: str) -> str | None:
        """
        Synchroner gradio_client-Aufruf.
        not-lain/background-removal: api_name="/png" liefert direkt PNG-Dateipfad.
        """
        from gradio_client import Client, handle_file

        client = Client(BIREFNET_SPACE, hf_token=hf_token)
        result = client.predict(
            f=handle_file(image_path),
            api_name="/png",
        )
        if result is None:
            return None
        if isinstance(result, dict) and "path" in result:
            return str(result["path"])
        if isinstance(result, str) and result:
            return result
        if isinstance(result, (list, tuple)) and result:
            item = result[0]
            if isinstance(item, dict) and "path" in item:
                return str(item["path"])
            if isinstance(item, str):
                return item
        return str(result) if result else None
