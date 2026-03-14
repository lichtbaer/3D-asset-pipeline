"""Storage-API: Statistik und Papierkorb-Purge."""

from fastapi import APIRouter

from app.services.storage_service import compute_storage_stats, purge_deleted

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/stats")
async def get_storage_stats():
    """Speicherverbrauch und Breakdown nach Typ (images, meshes, rigs, animations, exports)."""
    return compute_storage_stats()


@router.post("/purge-deleted")
async def purge_deleted_assets():
    """Löscht alle Assets mit deleted_at permanent. Gibt Anzahl und freigegebene Bytes zurück."""
    count, freed = purge_deleted()
    return {"deleted_count": count, "freed_bytes": freed}
