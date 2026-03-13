"""
Abstrakte Basisklasse für Animation-Provider.
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class AnimationParams(BaseModel):
    """Parameter für Animation-Generierung."""

    source_glb_url: str  # URL zu mesh_rigged.glb (oder mesh.glb)
    motion_prompt: str  # z.B. "walk forward", "jump", "wave hand"
    asset_id: str | None = None


class AnimationResult(BaseModel):
    """Ergebnis einer Animation-Generierung."""

    animated_glb_bytes: bytes
    provider_key: str
    output_format: str = "glb"  # "glb" oder "fbx" je nach Provider


class MotionPreset(BaseModel):
    """Vordefiniertes Motion-Preset."""

    key: str
    display_name: str
    prompt: str  # interner Prompt der an den Provider geht


class BaseAnimationProvider(ABC):
    """Basisklasse für austauschbare Animation-Backends (HF Spaces, etc.)."""

    key: str
    display_name: str

    @abstractmethod
    async def animate(self, params: AnimationParams) -> AnimationResult:
        """
        Generiert Animation aus gerüggtem GLB + Motion-Prompt.
        Gibt die animierte GLB als Bytes zurück.
        """
        ...

    @abstractmethod
    def get_preset_motions(self) -> list[MotionPreset]:
        """Liefert die verfügbaren Motion-Presets."""
        ...
