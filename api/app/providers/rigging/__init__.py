"""
Rigging-Provider-Abstraktion: austauschbare Rigging-Backends (UniRig, etc.).
"""
from app.providers.rigging.base import BaseRiggingProvider, RiggingParams, RiggingResult
from app.providers.rigging.registry import (
    RIGGING_PROVIDER_REGISTRY,
    get_rigging_provider,
    list_rigging_providers,
)
from app.providers.rigging.registry import (
    list_available_keys as list_rigging_available_keys,
)

__all__ = [
    "BaseRiggingProvider",
    "RiggingParams",
    "RiggingResult",
    "RIGGING_PROVIDER_REGISTRY",
    "get_rigging_provider",
    "list_rigging_available_keys",
    "list_rigging_providers",
]
