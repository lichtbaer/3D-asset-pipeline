"""Provider-Registry für Image-Provider."""

from app.services.image_providers.base import ImageProvider
from app.services.image_providers.picsart import create_picsart_providers

_REGISTRY: dict[str, ImageProvider] = {}

# PicsArt-Provider beim Import registrieren
for provider in create_picsart_providers():
    _REGISTRY[provider.provider_key] = provider


def get_provider(key: str) -> ImageProvider:
    """
    Liefert den Provider für den gegebenen Key.

    Raises:
        ValueError: Bei unbekanntem provider_key
    """
    if key not in _REGISTRY:
        raise ValueError(f"Unbekannter provider_key: {key}")
    return _REGISTRY[key]


def list_providers() -> list[ImageProvider]:
    """Liefert alle registrierten Image-Provider."""
    return list(_REGISTRY.values())
