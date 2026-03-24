"""Provider-Registry für Image-Provider."""

import logging

from app.exceptions import ProviderConfigError
from app.services.image_providers.base import ImageProvider
from app.services.image_providers.picsart import create_picsart_providers

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, ImageProvider] = {}

for _provider in create_picsart_providers():
    _REGISTRY[_provider.provider_key] = _provider

try:
    from app.services.image_providers.hf_inference import HFInferenceImageProvider

    _REGISTRY["hf-inference"] = HFInferenceImageProvider()
    logger.info("hf-inference Provider erfolgreich registriert")
except ProviderConfigError as _e:
    logger.warning("hf-inference Provider nicht verfügbar: %s", _e)

try:
    from app.services.image_providers.replicate_provider import ReplicateImageProvider

    _REGISTRY["replicate"] = ReplicateImageProvider()
    logger.info("replicate Provider erfolgreich registriert")
except ProviderConfigError as _e:
    logger.warning("replicate Provider nicht verfügbar: %s", _e)


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


def list_available_keys() -> list[str]:
    """Liefert die Keys aller registrierten Image-Provider."""
    return list(_REGISTRY.keys())
