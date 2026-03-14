"""
TRELLIS.2 (Microsoft) Mesh-Provider via Hugging Face Space.
4B-Parameter Modell mit PBR-Materialien und O-Voxel-Repräsentation.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from gradio_client import Client, handle_file

from app.exceptions import Trellis2InvalidImageError, Trellis2TimeoutError
from app.services.mesh_providers.base import MeshProvider

logger = logging.getLogger(__name__)

TRELLIS2_SPACE = "microsoft/TRELLIS.2"
MESH_TIMEOUT_SEC = 300


class Trellis2Provider(MeshProvider):
    provider_key = "trellis2"
    display_name = "TRELLIS.2 (Microsoft)"

    def default_params(self) -> dict[str, Any]:
        return {
            "seed": 0,
            "resolution": "1024",
            "ss_guidance_strength": 7.5,
            "ss_sampling_steps": 12,
            "shape_slat_guidance_strength": 7.5,
            "shape_slat_sampling_steps": 12,
            "tex_slat_guidance_strength": 1.0,
            "tex_slat_sampling_steps": 12,
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
                "resolution": {
                    "type": "string",
                    "enum": ["512", "1024", "1536"],
                    "default": "1024",
                    "description": "Auflösung (512 schnell, 1536 höchste Qualität)",
                },
                "ss_guidance_strength": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 20,
                    "default": 7.5,
                    "description": "Sparse Structure Guidance Strength",
                },
                "ss_sampling_steps": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 12,
                    "description": "Sparse Structure Sampling Steps",
                },
                "shape_slat_guidance_strength": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 20,
                    "default": 7.5,
                    "description": "Shape SLAT Guidance Strength",
                },
                "shape_slat_sampling_steps": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 12,
                    "description": "Shape SLAT Sampling Steps",
                },
                "tex_slat_guidance_strength": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 20,
                    "default": 1.0,
                    "description": "Texture SLAT Guidance Strength",
                },
                "tex_slat_sampling_steps": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 12,
                    "description": "Texture SLAT Sampling Steps",
                },
            },
            "required": [],
        }

    def _run_predict(self, image_path: str, params: dict[str, Any], hf_token: str) -> str | None:
        """
        Synchroner Aufruf: /image_to_3d → /extract_glb.
        Gibt den Pfad zur GLB-Datei zurück oder None bei Fehler.
        """
        client = Client(TRELLIS2_SPACE, token=hf_token)

        # 1. image_to_3d generiert 3D-Asset (speichert State serverseitig)
        merged = {**self.default_params(), **params}
        client.predict(
            image=handle_file(image_path),
            seed=merged.get("seed", 0),
            resolution=merged.get("resolution", "1024"),
            ss_guidance_strength=merged.get("ss_guidance_strength", 7.5),
            ss_guidance_rescale=merged.get("ss_guidance_rescale", 0.7),
            ss_sampling_steps=merged.get("ss_sampling_steps", 12),
            ss_rescale_t=merged.get("ss_rescale_t", 5.0),
            shape_slat_guidance_strength=merged.get("shape_slat_guidance_strength", 7.5),
            shape_slat_guidance_rescale=merged.get("shape_slat_guidance_rescale", 0.5),
            shape_slat_sampling_steps=merged.get("shape_slat_sampling_steps", 12),
            shape_slat_rescale_t=merged.get("shape_slat_rescale_t", 3.0),
            tex_slat_guidance_strength=merged.get("tex_slat_guidance_strength", 1.0),
            tex_slat_guidance_rescale=merged.get("tex_slat_guidance_rescale", 0.0),
            tex_slat_sampling_steps=merged.get("tex_slat_sampling_steps", 12),
            tex_slat_rescale_t=merged.get("tex_slat_rescale_t", 3.0),
            api_name="/image_to_3d",
        )

        # 2. extract_glb exportiert GLB aus dem generierten State
        result = client.predict(
            decimation_target=merged.get("decimation_target", 300000),
            texture_size=merged.get("texture_size", 2048),
            api_name="/extract_glb",
        )

        if result is None:
            return None
        if isinstance(result, (list, tuple)):
            for item in result:
                if item and isinstance(item, str) and Path(item).exists():
                    if item.endswith(".glb") or ".glb" in item:
                        return str(item)
            if result and result[0]:
                return str(result[0])
            return None
        return str(result) if result else None

    async def generate(self, image_path: str, params: dict[str, Any]) -> str:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN nicht konfiguriert")

        try:
            glb_path = await asyncio.wait_for(
                asyncio.to_thread(self._run_predict, image_path, params, hf_token),
                timeout=MESH_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            raise Trellis2TimeoutError("predict() timed out") from None

        if not glb_path or not Path(glb_path).exists():
            raise Trellis2InvalidImageError(
                0, "TRELLIS.2 lieferte keine GLB-Datei (ungültiges Bild?)"
            )

        return glb_path
