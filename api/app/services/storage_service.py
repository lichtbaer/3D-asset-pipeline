"""
Storage-Statistik und Papierkorb-Purge.
"""

import logging
from pathlib import Path
from typing import Any

from app.config.storage import ASSETS_STORAGE_PATH

from app.services import asset_service

logger = logging.getLogger(__name__)


def _dir_size(path: Path) -> int:
    """Rekursive Größe eines Verzeichnisses in Bytes."""
    total = 0
    try:
        for entry in path.iterdir():
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += _dir_size(entry)
    except OSError:
        pass
    return total


def _human_size(size_bytes: int) -> str:
    """Formatiert Bytes als menschenlesbare Größe (z.B. 44.9 GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _get_asset_breakdown(asset_id: str) -> dict[str, int]:
    """
    Gibt die Größe pro Typ (images, meshes, rigs, animations, exports)
    für ein Asset zurück. Keys sind die Typen, Values sind Bytes.
    """
    meta = asset_service.get_asset(asset_id)
    if not meta:
        return {}
    asset_path = asset_service.get_asset_dir(asset_id)
    if not asset_path.exists():
        return {}

    breakdown: dict[str, int] = {
        "images": 0,
        "meshes": 0,
        "rigs": 0,
        "animations": 0,
        "exports": 0,
    }

    # Image-Dateien (image, bgremoval steps)
    for step in ("image", "bgremoval"):
        if step in meta.steps and meta.steps[step].get("file"):
            f = asset_path / meta.steps[step]["file"]
            if f.is_file():
                breakdown["images"] += f.stat().st_size

    # Mesh-Dateien: mesh.glb, mesh_original.*, mesh_simplified_*.glb, mesh_repaired, mesh_clipped, mesh_cleaned
    for f in asset_path.iterdir():
        if f.is_file():
            name = f.name.lower()
            if name == "mesh.glb" or name.startswith("mesh_simplified") or name in ("mesh_repaired.glb", "mesh_clipped.glb", "mesh_cleaned.glb"):
                breakdown["meshes"] += f.stat().st_size
            elif name.startswith("mesh_original"):
                breakdown["meshes"] += f.stat().st_size

    # Rigging: mesh_rigged.glb
    if "rigging" in meta.steps and meta.steps["rigging"].get("file"):
        f = asset_path / meta.steps["rigging"]["file"]
        if f.is_file():
            breakdown["rigs"] += f.stat().st_size

    # Animation: mesh_animated.glb, mesh_animated.fbx
    if "animation" in meta.steps and meta.steps["animation"].get("file"):
        f = asset_path / meta.steps["animation"]["file"]
        if f.is_file():
            breakdown["animations"] += f.stat().st_size

    # Exports (STL, OBJ, PLY, GLTF aus exports-Array)
    for exp in meta.exports or []:
        out_file = exp.get("output_file") or exp.get("filename")
        if out_file:
            f = asset_path / out_file
            if f.is_file():
                breakdown["exports"] += f.stat().st_size

    return breakdown


def compute_storage_stats() -> dict[str, Any]:
    """
    Berechnet Storage-Statistik über alle Assets.
    Berücksichtigt soft-deleted Assets für deleted_count und deleted_size_bytes.
    """
    ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

    total_size_bytes = 0
    asset_count = 0
    deleted_count = 0
    deleted_size_bytes = 0

    breakdown: dict[str, dict[str, int]] = {
        "images": {"count": 0, "size_bytes": 0},
        "meshes": {"count": 0, "size_bytes": 0},
        "rigs": {"count": 0, "size_bytes": 0},
        "animations": {"count": 0, "size_bytes": 0},
        "exports": {"count": 0, "size_bytes": 0},
    }

    for path in ASSETS_STORAGE_PATH.iterdir():
        if not path.is_dir():
            continue
        asset_id = path.name
        meta = asset_service.get_asset(asset_id)
        if not meta:
            continue

        size = _dir_size(path)
        total_size_bytes += size

        if meta.deleted_at:
            deleted_count += 1
            deleted_size_bytes += size
        else:
            asset_count += 1

        bd = _get_asset_breakdown(asset_id)
        for typ, sz in bd.items():
            if typ in breakdown and sz > 0:
                breakdown[typ]["size_bytes"] += sz
                # Count nur für aktive (nicht gelöschte) Assets
                if meta.deleted_at is None:
                    breakdown[typ]["count"] += 1

    return {
        "total_size_bytes": total_size_bytes,
        "total_size_human": _human_size(total_size_bytes),
        "asset_count": asset_count,
        "deleted_count": deleted_count,
        "deleted_size_bytes": deleted_size_bytes,
        "breakdown": breakdown,
    }


def purge_deleted() -> tuple[int, int]:
    """
    Löscht alle Assets mit deleted_at permanent.
    Gibt (anzahl_geloescht, freigegebene_bytes) zurück.
    """
    count = 0
    freed = 0
    for path in list(ASSETS_STORAGE_PATH.iterdir()):
        if not path.is_dir():
            continue
        meta = asset_service.get_asset(path.name)
        if meta and meta.deleted_at:
            size = _dir_size(path)
            if asset_service.delete_asset(path.name, permanent=True):
                count += 1
                freed += size
    logger.info("Papierkorb geleert: %d Assets, %d Bytes freigegeben", count, freed)
    return count, freed
