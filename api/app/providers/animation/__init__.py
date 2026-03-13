"""Animation-Provider-Modul."""

from app.providers.animation.base import (
    AnimationParams,
    AnimationResult,
    BaseAnimationProvider,
    MotionPreset,
)
from app.providers.animation.registry import (
    ANIMATION_PROVIDER_REGISTRY,
    get_animation_provider,
    list_animation_providers,
)

__all__ = [
    "AnimationParams",
    "AnimationResult",
    "BaseAnimationProvider",
    "MotionPreset",
    "ANIMATION_PROVIDER_REGISTRY",
    "get_animation_provider",
    "list_animation_providers",
]
