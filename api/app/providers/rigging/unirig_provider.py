"""
UniRig Rigging-Provider via Hugging Face Space.
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

from gradio_client import Client, handle_file

from app.exceptions import UniRigInvalidMeshError, UniRigTimeoutError
from app.providers.rigging.base import BaseRiggingProvider, RiggingParams, RiggingResult

logger = logging.getLogger(__name__)

UNIRIG_SPACE = "MajorDaniel/UniRig"
UNIRIG_TIMEOUT_SEC = 300


class UniRigProvider(BaseRiggingProvider):
    """UniRig-Provider über Hugging Face Space."""

    key = "unirig"
    display_name = "UniRig (HF Space)"

    def __init__(self) -> None:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN nicht konfiguriert")
        self._client = Client(UNIRIG_SPACE, token=hf_token)

    def _run_predict(self, glb_path: str) -> str | None:
        """
        Synchroner Aufruf von gradio_client (blockiert).
        Gibt den Pfad zur rigged GLB-Datei zurück oder None bei Fehler.
        """
        # UniRig erwartet typischerweise eine 3D-Datei (GLB/OBJ/FBX)
        result = self._client.predict(
            handle_file(glb_path),
            api_name="/main",
        )
        if result is None:
            return None
        if isinstance(result, (list, tuple)):
            for item in result:
                if item and isinstance(item, str) and (
                    item.endswith(".glb") or item.endswith(".obj")
                ):
                    return str(item)
            if result and result[0]:
                return str(result[0])
            return None
        return str(result) if result else None

    async def rig(self, params: RiggingParams) -> RiggingResult:
        # 1. GLB von URL laden → temp file
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(params.source_glb_url)
            response.raise_for_status()
            glb_bytes = response.content

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            f.write(glb_bytes)
            temp_path = f.name

        try:
            # 2. gradio_client.predict() aufrufen (blocking → asyncio.to_thread)
            result_path = await asyncio.wait_for(
                asyncio.to_thread(self._run_predict, temp_path),
                timeout=UNIRIG_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            raise UniRigTimeoutError(
                f"UniRig predict() timed out after {UNIRIG_TIMEOUT_SEC}s"
            )
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except OSError:
                pass

        if not result_path or not Path(result_path).exists():
            raise UniRigInvalidMeshError("UniRig lieferte keine rigged GLB; Mesh evtl. nicht riggbar")

        # 3. Output-GLB laden → bytes
        rigged_bytes = Path(result_path).read_bytes()
        return RiggingResult(
            rigged_glb_bytes=rigged_bytes,
            provider_key=self.key,
        )
