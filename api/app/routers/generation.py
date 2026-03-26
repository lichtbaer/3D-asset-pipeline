"""Generation router – thin aggregator that includes all sub-routers."""

from fastapi import APIRouter

from app.providers.animation import list_animation_available_keys
from app.providers.rigging import list_rigging_available_keys
from app.routers import (
    generation_animation,
    generation_bgremoval,
    generation_image,
    generation_jobs,
    generation_mesh,
    generation_rigging,
)
from app.services.bgremoval_providers.registry import (
    list_available_keys as list_bgremoval_available_keys,
)
from app.services.image_providers.registry import (
    list_available_keys as list_image_available_keys,
)
from app.services.mesh_providers.registry import (
    list_available_keys as list_mesh_available_keys,
)

router = APIRouter(prefix="/generate", tags=["generation"])

# Include all sub-routers (they use no prefix/tags of their own)
router.include_router(generation_image.router)
router.include_router(generation_bgremoval.router)
router.include_router(generation_mesh.router)
router.include_router(generation_rigging.router)
router.include_router(generation_animation.router)
router.include_router(generation_jobs.router)


@router.get("/providers")
async def list_all_available_providers():
    """Listet alle verfügbaren Provider je Typ (nur tatsächlich geladene)."""
    return {
        "image": list_image_available_keys(),
        "mesh": list_mesh_available_keys(),
        "bgremoval": list_bgremoval_available_keys(),
        "rigging": list_rigging_available_keys(),
        "animation": list_animation_available_keys(),
    }
