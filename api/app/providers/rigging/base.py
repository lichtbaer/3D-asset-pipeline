"""
Abstrakte Basisklasse für Rigging-Provider.
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class RiggingParams(BaseModel):
    """Parameter für Rigging-Aufruf."""

    source_glb_url: str
    asset_id: str | None = None


class RiggingResult(BaseModel):
    """Ergebnis eines Rigging-Aufrufs."""

    rigged_glb_bytes: bytes
    provider_key: str


class ProviderInfo(BaseModel):
    """Info über einen Rigging-Provider für GET /generate/rigging/providers."""

    key: str
    display_name: str


class BaseRiggingProvider(ABC):
    """Basisklasse für austauschbare Rigging-Backends (HF Spaces, etc.)."""

    key: str
    display_name: str

    @abstractmethod
    async def rig(self, params: RiggingParams) -> RiggingResult:
        """
        Erzeugt ein Rig (Armature + Skin-Weights) aus dem Mesh.
        Gibt die rigged GLB als Bytes zurück.
        """
        ...

    def get_info(self) -> ProviderInfo:
        """Liefert Provider-Info für die API."""
        return ProviderInfo(key=self.key, display_name=self.display_name)
