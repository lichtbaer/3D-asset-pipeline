"""Abstrakte Basisklasse für Background-Removal-Provider."""

from abc import ABC, abstractmethod
from typing import Any


class BgRemovalProvider(ABC):
    """Basisklasse für austauschbare Background-Removal-Backends."""

    provider_key: str
    display_name: str

    @abstractmethod
    async def remove_background(
        self, image_url: str, *, job_id: str | None = None
    ) -> str:
        """
        Entfernt den Hintergrund eines Bildes.

        Args:
            image_url: URL des Quellbilds
            job_id: Optional Job-ID für lokale Provider (Speicherpfad)

        Returns:
            URL des freigestellten Bilds
        """
        ...

    def default_params(self) -> dict[str, Any]:
        """Provider-spezifische Standard-Parameter (optional)."""
        return {}

    @abstractmethod
    def param_schema(self) -> dict[str, Any]:
        """
        JSON Schema für provider-spezifische Parameter.
        Wird an Frontend für dynamisches Formular zurückgegeben.
        """
        ...
