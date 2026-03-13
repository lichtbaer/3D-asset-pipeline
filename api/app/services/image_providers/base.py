"""Abstrakte Basisklasse für Image-Provider."""

from abc import ABC, abstractmethod


class ImageProvider(ABC):
    """Basisklasse für Bildgenerierungs-Provider."""

    provider_key: str
    display_name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        params: dict,
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
    def default_params(self) -> dict:
        """Liefert die Standard-Parameter für diesen Provider."""
        ...

    @abstractmethod
    def param_schema(self) -> dict:
        """
        JSON Schema für provider-spezifische Parameter.
        Wird an Frontend für dynamisches Formular zurückgegeben.
        """
        ...
