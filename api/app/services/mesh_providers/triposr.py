"""
TripoSR Mesh-Provider via Hugging Face Space.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path

from gradio_client import Client, handle_file

from app.config.storage import MESH_STORAGE_PATH
from app.services.mesh_providers.base import MeshProvider

logger = logging.getLogger(__name__)

TRIPOSR_SPACE = "stabilityai/TripoSR"
MESH_TIMEOUT_SEC = 300


class TripoSRProvider(MeshProvider):
    provider_key = "triposr"
    display_name = "TripoSR"

    def default_params(self) -> dict:
        return {"mc_resolution": 256}

    def param_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "mc_resolution": {
                    "type": "integer",
                    "minimum": 128,
                    "maximum": 512,
                    "default": 256,
                    "description": "Marching Cubes Auflösung für Mesh-Extraktion",
                }
            },
            "required": [],
        }

    def _run_predict(
        self, image_path: str, mc_resolution: int, hf_token: str
    ) -> str | None:
        """
        Synchroner Aufruf von gradio_client.
        Gibt den Pfad zur GLB-Datei zurück oder None bei Fehler.
        """
        client = Client(TRIPOSR_SPACE, hf_token=hf_token)
        # TripoSR Space API: /predict mit image und mc_resolution
        result = client.predict(
            image=handle_file(image_path),
            mc_resolution=mc_resolution,
            api_name="/predict",
        )
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
        mc_resolution = params.get(
            "mc_resolution", self.default_params()["mc_resolution"]
        )
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN nicht konfiguriert")

        glb_path = await asyncio.wait_for(
            asyncio.to_thread(
                self._run_predict, image_path, mc_resolution, hf_token
            ),
            timeout=MESH_TIMEOUT_SEC,
        )

        if not glb_path or not Path(glb_path).exists():
            raise RuntimeError("TripoSR lieferte keine GLB-Datei")

        return glb_path
