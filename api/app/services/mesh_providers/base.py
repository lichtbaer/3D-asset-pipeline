"""
Abstrakte Basisklasse für Mesh-Provider.
"""
from abc import ABC, abstractmethod


class MeshProvider(ABC):
    """Basisklasse für austauschbare Mesh-Generierungs-Backends (HF Spaces, etc.)."""

    provider_key: str  # z.B. "hunyuan3d-2", "triposr"
    display_name: str

    @abstractmethod
    async def generate(
        self,
        image_path: str,  # lokaler Pfad zum heruntergeladenen Bild
        params: dict,  # provider-spezifische Parameter
    ) -> str:
        """
        Generiert ein 3D-Mesh aus dem Bild.
        Gibt den lokalen Pfad zur GLB-Datei zurück.
        """
        ...

    @abstractmethod
    def default_params(self) -> dict:
        """Provider-spezifische Standard-Parameter."""
        ...

    @abstractmethod
    def param_schema(self) -> dict:
        """
        JSON Schema für provider-spezifische Parameter.
        Wird an Frontend für dynamisches Formular zurückgegeben.
        """
        ...
