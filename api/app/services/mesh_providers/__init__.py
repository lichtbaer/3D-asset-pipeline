"""
Mesh-Provider-Abstraktion: austauschbare HF-Space-Backends.
"""
from app.services.mesh_providers.base import MeshProvider
from app.services.mesh_providers.registry import MESH_PROVIDERS, get_provider

__all__ = [
    "MeshProvider",
    "MESH_PROVIDERS",
    "get_provider",
]
