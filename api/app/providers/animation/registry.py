"""
Provider-Registry und Lookup für Animation-Generierung.
"""
from app.providers.animation.base import BaseAnimationProvider
from app.providers.animation.hymotion_provider import HYMotionProvider

ANIMATION_PROVIDER_REGISTRY: dict[str, BaseAnimationProvider] = {
    "hy-motion": HYMotionProvider(),
}


def get_animation_provider(key: str) -> BaseAnimationProvider:
    """Liefert den Animation-Provider für den angegebenen Key."""
    if key not in ANIMATION_PROVIDER_REGISTRY:
        raise ValueError(f"Unknown animation provider: {key}")
    return ANIMATION_PROVIDER_REGISTRY[key]


def list_animation_providers() -> list[BaseAnimationProvider]:
    """Liefert alle registrierten Animation-Provider."""
    return list(ANIMATION_PROVIDER_REGISTRY.values())
