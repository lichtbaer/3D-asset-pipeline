"""
HY-Motion (Hunyuan Motion) Provider via Hugging Face Space tencent/HY-Motion-1.0.

Hinweis: Der aktuelle HF Space ist text-to-motion und liefert FBX.
Die Spec erwartet GLB; wir speichern die API-Ausgabe (FBX) als mesh_animated.fbx.
Bei Verfügbarkeit eines GLB-fähigen Spaces kann die Implementierung angepasst werden.
"""
import asyncio
import logging
import os
from pathlib import Path

from gradio_client import Client

from app.providers.animation.base import (
    AnimationParams,
    AnimationResult,
    BaseAnimationProvider,
    MotionPreset,
)

logger = logging.getLogger(__name__)

HY_MOTION_SPACE = "tencent/HY-Motion-1.0"
ANIMATION_TIMEOUT_SEC = 300


class HYMotionProvider(BaseAnimationProvider):
    key = "hy-motion"
    display_name = "HY-Motion (Hunyuan)"

    def __init__(self) -> None:
        self._client: Client | None = None

    def _get_client(self) -> Client:
        """Lazy-Init Client (HF_TOKEN für private Spaces)."""
        if self._client is None:
            hf_token = os.getenv("HF_TOKEN")
            self._client = Client(HY_MOTION_SPACE, hf_token=hf_token or "")
        return self._client

    def _run_predict(
        self,
        motion_prompt: str,
        hf_token: str | None,
    ) -> bytes | None:
        """
        Synchroner Aufruf von gradio_client (blockiert).
        HY-Motion-1.0: text-to-motion, liefert FBX.
        Gibt Datei-Bytes zurück oder None bei Fehler.
        """
        client = Client(HY_MOTION_SPACE, hf_token=hf_token or "")
        # Prompt-Engineering optional; für MVP nutzen wir Prompt direkt
        rewritten = motion_prompt
        result = client.predict(
            original_text=motion_prompt,
            rewritten_text=rewritten,
            seed_input="0,1,2,3",
            motion_duration=5.0,
            cfg_scale=5.0,
            api_name="/generate_motion_func",
        )
        if result is None:
            return None
        # Returns: (value_27: Html, _download_fbx_files: List[filepath])
        if isinstance(result, (list, tuple)) and len(result) >= 2:
            fbx_list = result[1]
            if fbx_list and isinstance(fbx_list, list) and len(fbx_list) > 0:
                first_path = fbx_list[0]
                if isinstance(first_path, str) and Path(first_path).exists():
                    return Path(first_path).read_bytes()
            # Einzelner Pfad
            if isinstance(fbx_list, str) and Path(fbx_list).exists():
                return Path(fbx_list).read_bytes()
        return None

    async def animate(self, params: AnimationParams) -> AnimationResult:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError(
                "HF_TOKEN nicht konfiguriert. Animation-Provider benötigt Hugging Face Token."
            )

        # source_glb_url wird von der Spec verlangt; HY-Motion-1.0 nutzt sie aktuell nicht
        # (text-to-motion). Für zukünftige Spaces, die GLB+Motion unterstützen.
        _ = params.source_glb_url

        animated_bytes = await asyncio.wait_for(
            asyncio.to_thread(
                self._run_predict,
                params.motion_prompt,
                hf_token,
            ),
            timeout=ANIMATION_TIMEOUT_SEC,
        )

        if not animated_bytes:
            raise RuntimeError("HY-Motion lieferte keine Animationsdatei")

        return AnimationResult(
            animated_glb_bytes=animated_bytes,
            provider_key=self.key,
            output_format="fbx",  # HY-Motion-1.0 liefert FBX
        )

    def get_preset_motions(self) -> list[MotionPreset]:
        return [
            MotionPreset(
                key="walk",
                display_name="Gehen",
                prompt="character walking forward naturally",
            ),
            MotionPreset(
                key="run",
                display_name="Laufen",
                prompt="character running forward",
            ),
            MotionPreset(
                key="idle",
                display_name="Idle",
                prompt="character standing idle, breathing",
            ),
            MotionPreset(
                key="jump",
                display_name="Springen",
                prompt="character jumping up",
            ),
            MotionPreset(
                key="wave",
                display_name="Winken",
                prompt="character waving hand",
            ),
        ]
