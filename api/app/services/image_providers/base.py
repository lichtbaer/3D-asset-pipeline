"""Abstrakte Basisklasse für Image-Provider."""

from abc import ABC, abstractmethod
from typing import Any


class ImageProvider(ABC):
    """Basisklasse für Bildgenerierungs-Provider."""

    provider_key: str
    display_name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        params: dict[str, Any],
    ) -> str:
        """
        Generiert ein Bild und gibt die URL zurück.

        Args:
            prompt: Text-Prompt für die Bildgenerierung
            params: Provider-spezifische Parameter (width, height, etc.)

        Returns:
            URL des generierten Bildes
        """
        ...

    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """Liefert die Standard-Parameter für diesen Provider."""
        ...

    @abstractmethod
    def param_schema(self) -> dict[str, Any]:
        """
        JSON Schema für provider-spezifische Parameter.
        Wird an Frontend für dynamisches Formular zurückgegeben.
        """
        ...
