"""
Asset-Import: Erstellt Assets aus hochgeladenen Bildern und 3D-Modellen.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.asset_paths import AssetPaths
from app.services.asset_service import create_asset
from app.services.metadata_service import get_metadata_service

logger = logging.getLogger(__name__)


def create_asset_from_image_upload(
    file_bytes: bytes,
    filename: str,
    name: str | None = None,
) -> str:
    """
    Erstellt Asset aus hochgeladenem Bild.
    Speichert Bild als image_original.{ext}, metadata mit source: upload.
    """
    asset_id = create_asset()
    paths = AssetPaths(asset_id)
    ext = Path(filename).suffix.lower() or ".png"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".png"
    target_filename = f"image_original{ext}"
    paths.processing_file(target_filename).write_bytes(file_bytes)

    display_name = name or Path(filename).stem
    now = datetime.now(timezone.utc).isoformat()
    step_data: dict[str, Any] = {
        "job_id": "",
        "provider_key": "upload",
        "file": target_filename,
        "generated_at": now,
        "source": "upload",
        "original_filename": filename,
        "uploaded_at": now,
        "name": display_name,
    }

    meta = get_metadata_service().read(asset_id)
    meta["steps"]["image"] = step_data
    meta["source"] = "upload"
    meta["original_filename"] = filename
    meta["uploaded_at"] = now
    meta["updated_at"] = now
    get_metadata_service().write(asset_id, meta)
    return asset_id


def create_asset_from_mesh_upload(
    file_bytes: bytes,
    filename: str,
    name: str | None = None,
    mtl_bytes: bytes | None = None,
    mtl_filename: str | None = None,
) -> str:
    """
    Erstellt Asset aus hochgeladenem 3D-Modell.
    Konvertiert STL/OBJ/PLY zu GLB via trimesh, speichert Original als mesh_original.{ext}.
    """
    import tempfile
    import zipfile
    from io import BytesIO

    import trimesh

    asset_id = create_asset()
    paths = AssetPaths(asset_id)
    ext = Path(filename).suffix.lower()

    # Original behalten
    original_ext = ext or ".glb"
    original_filename = f"mesh_original{original_ext}"
    paths.processing_file(original_filename).write_bytes(file_bytes)

    # Temp-Verzeichnis für Laden (OBJ braucht ggf. MTL im selben Ordner)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        load_path: Path

        if ext == ".zip":
            with zipfile.ZipFile(BytesIO(file_bytes), "r") as zf:
                zf.extractall(tmp)
            obj_files = list(tmp.rglob("*.obj"))
            if not obj_files:
                raise ValueError("ZIP enthält keine OBJ-Datei")
            load_path = obj_files[0]
        else:
            mesh_path = tmp / filename
            mesh_path.write_bytes(file_bytes)
            if mtl_bytes and mtl_filename:
                (tmp / mtl_filename).write_bytes(mtl_bytes)
            load_path = mesh_path

        try:
            scene = trimesh.load(str(load_path), force="mesh")
        except (ValueError, OSError, RuntimeError) as e:
            raise ValueError(f"3D-Modell konnte nicht geladen werden: {e}") from e

        # Scene oder einzelnes Mesh zu einem Mesh zusammenführen
        if isinstance(scene, trimesh.Scene):
            meshes = list(scene.geometry.values())
            if not meshes:
                raise ValueError("3D-Modell enthält keine Meshes")
                mesh = trimesh.util.concatenate(meshes)
        elif isinstance(scene, trimesh.Trimesh):
            mesh = scene
        else:
            raise ValueError("Unbekanntes 3D-Format")

        glb_data = mesh.export(file_type="glb")
        if isinstance(glb_data, dict):
            paths.mesh.write_bytes(json.dumps(glb_data).encode("utf-8"))
        elif isinstance(glb_data, str):
            paths.mesh.write_bytes(glb_data.encode("utf-8"))
        else:
            paths.mesh.write_bytes(glb_data)

    display_name = name or Path(filename).stem
    now = datetime.now(timezone.utc).isoformat()
    original_format = ext.lstrip(".") if ext else "glb"
    step_data: dict[str, Any] = {
        "job_id": "",
        "provider_key": "upload",
        "file": "mesh.glb",
        "generated_at": now,
        "source": "upload",
        "original_filename": filename,
        "original_format": original_format,
        "uploaded_at": now,
        "name": display_name,
    }

    meta = get_metadata_service().read(asset_id)
    meta["steps"]["mesh"] = step_data
    meta["source"] = "upload"
    meta["original_filename"] = filename
    meta["original_format"] = original_format
    meta["uploaded_at"] = now
    meta["updated_at"] = now
    get_metadata_service().write(asset_id, meta)
    return asset_id
