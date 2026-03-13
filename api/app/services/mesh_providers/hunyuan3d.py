"""
Hunyuan3D-2 Mesh-Provider via Hugging Face Space.
"""
import asyncio
import logging
import os
from pathlib import Path

from gradio_client import Client, handle_file

from app.services.mesh_providers.base import MeshProvider

logger = logging.getLogger(__name__)

HUNYUAN_SPACE = "tencent/Hunyuan3D-2"
MESH_TIMEOUT_SEC = 300


class Hunyuan3DProvider(MeshProvider):
    provider_key = "hunyuan3d-2"
    display_name = "Hunyuan3D-2"

    def default_params(self) -> dict:
        return {"steps": 30}

    def param_schema(self) -> dict:
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
        if result is None:
            return None
        if isinstance(result, (list, tuple)):
            for item in result:
                if item and isinstance(item, str) and (
                    item.endswith(".glb") or item.endswith(".obj")
                ):
                    return item
            if result and result[0]:
                return str(result[0])
            return None
        return str(result) if result else None

    async def generate(self, image_path: str, params: dict) -> str:
        steps = params.get("steps", self.default_params()["steps"])
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN nicht konfiguriert")

        glb_path = await asyncio.wait_for(
            asyncio.to_thread(
                self._run_predict, image_path, steps, hf_token
            ),
            timeout=MESH_TIMEOUT_SEC,
        )

        if not glb_path or not Path(glb_path).exists():
            raise RuntimeError("Hunyuan3D-2 lieferte keine GLB-Datei")

        return glb_path
