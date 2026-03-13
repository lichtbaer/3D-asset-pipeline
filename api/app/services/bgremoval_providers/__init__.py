"""Background-Removal-Provider-Abstraktion — austauschbare Backends."""

from app.services.bgremoval_providers.base import BgRemovalProvider
from app.services.bgremoval_providers.registry import (
    BGREMOVAL_PROVIDERS,
    get_provider,
    list_providers,
)

__all__ = [
    "BgRemovalProvider",
    "BGREMOVAL_PROVIDERS",
    "get_provider",
    "list_providers",
]
