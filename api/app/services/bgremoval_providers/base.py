"""Abstrakte Basisklasse für Background-Removal-Provider."""

from abc import ABC, abstractmethod


class BgRemovalProvider(ABC):
    """Basisklasse für austauschbare Background-Removal-Backends."""

    provider_key: str
    display_name: str

    @abstractmethod
    async def remove_background(self, image_url: str) -> str:
        """
        Entfernt den Hintergrund eines Bildes.

        Args:
            image_url: URL des Quellbilds

        Returns:
            URL des freigestellten Bilds
        """
        ...

    def default_params(self) -> dict:
        """Provider-spezifische Standard-Parameter (optional)."""
        return {}

    @abstractmethod
    def param_schema(self) -> dict:
        """
        JSON Schema für provider-spezifische Parameter.
        Wird an Frontend für dynamisches Formular zurückgegeben.
        """
        ...
