"""
Abstrakte Basisklasse für Mesh-Provider.
"""
from abc import ABC, abstractmethod
from typing import Any


class MeshProvider(ABC):
    """Basisklasse für austauschbare Mesh-Generierungs-Backends (HF Spaces, etc.)."""

    provider_key: str  # z.B. "hunyuan3d-2", "triposr"
    display_name: str

    @abstractmethod
    async def generate(
        self,
        image_path: str,  # lokaler Pfad zum heruntergeladenen Bild
        params: dict[str, Any],  # provider-spezifische Parameter
    ) -> str:
        """
        Generiert ein 3D-Mesh aus dem Bild.
        Gibt den lokalen Pfad zur GLB-Datei zurück.
        """
        ...

    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """Provider-spezifische Standard-Parameter."""
        ...

    @abstractmethod
    def param_schema(self) -> dict[str, Any]:
        """
        JSON Schema für provider-spezifische Parameter.
        Wird an Frontend für dynamisches Formular zurückgegeben.
        """
        ...

    @staticmethod
    def _extract_glb_path(result: Any) -> str | None:
        """
        Extrahiert den GLB/OBJ-Pfad aus einem Gradio-Ergebnis.
        Gradio gibt je nach Space ein str, list oder tuple zurück.
        """
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
