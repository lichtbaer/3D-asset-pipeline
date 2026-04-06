"""
Hunyuan3D-2 Mesh-Provider via Hugging Face Space.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from gradio_client import Client, handle_file

from app.core.config import settings
from app.services.mesh_providers.base import MeshProvider

logger = logging.getLogger(__name__)

HUNYUAN_SPACE = "tencent/Hunyuan3D-2"


class Hunyuan3DProvider(MeshProvider):
    provider_key = "hunyuan3d-2"
    display_name = "Hunyuan3D-2"

    def default_params(self) -> dict[str, Any]:
        return {"steps": 30}

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 30,
                    "description": "Anzahl der Inferenz-Schritte",
                }
            },
            "required": [],
        }

    def _run_predict(self, image_path: str, steps: int, hf_token: str) -> str | None:
        """
        Synchroner Aufruf von gradio_client (blockiert).
        Gibt den Pfad zur GLB-Datei zurück oder None bei Fehler.
        """
        client = Client(HUNYUAN_SPACE, token=hf_token)
        result = client.predict(
            image=handle_file(image_path),
            steps=steps,
            api_name="/generation_all",
        )
        # /generation_all returns (file, file, output, mesh_stats, seed) — erste Datei ist GLB
        return self._extract_glb_path(result)

    async def generate(self, image_path: str, params: dict[str, Any]) -> str:
        steps = params.get("steps", self.default_params()["steps"])
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN nicht konfiguriert")

        glb_path = await asyncio.wait_for(
            asyncio.to_thread(
                self._run_predict, image_path, steps, hf_token
            ),
            timeout=settings.MESH_GENERATION_TIMEOUT_S,
        )

        if not glb_path or not Path(glb_path).exists():
            raise RuntimeError("Hunyuan3D-2 lieferte keine GLB-Datei")

        return glb_path
