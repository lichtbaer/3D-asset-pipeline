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
from app.providers.animation.registry import (
    list_available_keys as list_animation_available_keys,
)

__all__ = [
    "AnimationParams",
    "AnimationResult",
    "BaseAnimationProvider",
    "MotionPreset",
    "ANIMATION_PROVIDER_REGISTRY",
    "get_animation_provider",
    "list_animation_providers",
    "list_animation_available_keys",
]
