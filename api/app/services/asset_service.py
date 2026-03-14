"""
Asset-Persistenz: Ordnerstruktur mit Metadaten für alle Pipeline-Outputs.
Jeder generierte Output wird auf dem Filesystem abgelegt.
"""

import asyncio
import json
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config.storage import (
    ASSETS_STORAGE_PATH,
    BGREMOVAL_STORAGE_PATH,
    MESH_STORAGE_PATH,
)

logger = logging.getLogger(__name__)

# Step-Typen für metadata.json
StepType = str  # "image" | "bgremoval" | "mesh"


class AssetMetadata:
    """Repräsentation der metadata.json eines Assets."""

    def __init__(
        self,
        asset_id: str,
        created_at: str,
        updated_at: str,
        steps: dict[str, dict[str, Any]],
        processing: list[dict[str, Any]] | None = None,
        sketchfab_upload: dict[str, Any] | None = None,
        source: str | None = None,
        sketchfab_uid: str | None = None,
        sketchfab_url: str | None = None,
        sketchfab_author: str | None = None,
        downloaded_at: str | None = None,
        exports: list[dict[str, Any]] | None = None,
    ):
        self.asset_id = asset_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.steps = steps
        self.processing = processing or []
        self.sketchfab_upload = sketchfab_upload
        self.source = source
        self.sketchfab_uid = sketchfab_uid
        self.sketchfab_url = sketchfab_url
        self.sketchfab_author = sketchfab_author
        self.downloaded_at = downloaded_at
        self.exports = exports or []

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "asset_id": self.asset_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": self.steps,
            "processing": self.processing,
            "exports": self.exports,
        }
        if self.sketchfab_upload is not None:
            out["sketchfab_upload"] = self.sketchfab_upload
        if self.source is not None:
            out["source"] = self.source
        if self.sketchfab_uid is not None:
            out["sketchfab_uid"] = self.sketchfab_uid
        if self.sketchfab_url is not None:
            out["sketchfab_url"] = self.sketchfab_url
        if self.sketchfab_author is not None:
            out["sketchfab_author"] = self.sketchfab_author
        if self.downloaded_at is not None:
            out["downloaded_at"] = self.downloaded_at
        return out


def _asset_dir(asset_id: str) -> Path:
    return ASSETS_STORAGE_PATH / asset_id


def _metadata_path(asset_id: str) -> Path:
    return _asset_dir(asset_id) / "metadata.json"


def create_asset() -> str:
    """
    Legt Ordner + leere metadata.json an, gibt asset_id zurück.
    """
    asset_id = str(uuid.uuid4())
    asset_path = _asset_dir(asset_id)
    asset_path.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": {},
    }
    _metadata_path(asset_id).write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return asset_id


async def update_step(
    asset_id: str,
    step: StepType,
    data: dict[str, Any],
    file_bytes: bytes | None = None,
    filename: str | None = None,
) -> None:
    """
    Schreibt Datei (falls file_bytes) und aktualisiert metadata.json.
    data enthält: job_id, provider_key, prompt/negative_prompt/source_file, etc.
    Verwendet asyncio.to_thread, um blockierendes File-I/O aus dem Event-Loop auszulagern.
    """
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")

    if file_bytes is not None and filename:
        target = asset_path / filename
        await asyncio.to_thread(target.write_bytes, file_bytes)
        data["file"] = filename

    meta_path = _metadata_path(asset_id)

    def _update_meta() -> None:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["steps"][step] = data
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    await asyncio.to_thread(_update_meta)


def get_asset(asset_id: str) -> AssetMetadata | None:
    """Liest metadata.json, gibt None wenn nicht vorhanden."""
    meta_path = _metadata_path(asset_id)
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return AssetMetadata(
        asset_id=data["asset_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        steps=data.get("steps", {}),
        processing=data.get("processing", []),
        sketchfab_upload=data.get("sketchfab_upload"),
        source=data.get("source"),
        sketchfab_uid=data.get("sketchfab_uid"),
        sketchfab_url=data.get("sketchfab_url"),
        sketchfab_author=data.get("sketchfab_author"),
        downloaded_at=data.get("downloaded_at"),
        exports=data.get("exports", []),
    )


def list_assets() -> list[AssetMetadata]:
    """Alle Assets sortiert nach created_at desc."""
    ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    assets: list[AssetMetadata] = []
    for path in ASSETS_STORAGE_PATH.iterdir():
        if path.is_dir():
            meta = get_asset(path.name)
            if meta:
                assets.append(meta)
    assets.sort(key=lambda a: a.created_at, reverse=True)
    return assets


def get_file_path(asset_id: str, filename: str) -> Path | None:
    """Pfad zur Datei, None wenn nicht vorhanden oder Pfad ungültig.

    Validiert asset_id als UUID und verhindert Path-Traversal-Angriffe.
    """
    if not re.fullmatch(r"[0-9a-f-]{36}", asset_id):
        return None
    base = _asset_dir(asset_id).resolve()
    target = (base / filename).resolve()
    if not target.is_relative_to(base):
        return None
    return target if target.is_file() else None


def get_asset_dir(asset_id: str) -> Path:
    """Asset-Ordner-Pfad. Erstellt nicht automatisch."""
    return _asset_dir(asset_id)


def write_asset_file(asset_id: str, filename: str, data: bytes) -> None:
    """Schreibt Datei in Asset-Ordner."""
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    (asset_path / filename).write_bytes(data)


def list_mesh_files(asset_id: str) -> list[str]:
    """Listet alle GLB-Dateien im Asset-Ordner (für Mesh-Processing-Quelle)."""
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        return []
    return sorted(
        f.name for f in asset_path.iterdir()
        if f.is_file() and f.suffix.lower() == ".glb"
    )


def append_processing_entry(asset_id: str, entry: dict[str, Any]) -> None:
    """Fügt Eintrag zum processing-Array in metadata.json hinzu."""
    meta_path = _metadata_path(asset_id)
    if not meta_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "processing" not in meta:
        meta["processing"] = []
    meta["processing"].append(entry)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def update_metadata_fields(asset_id: str, fields: dict[str, Any]) -> None:
    """Aktualisiert Top-Level-Felder in metadata.json (z.B. sketchfab_upload, source)."""
    meta_path = _metadata_path(asset_id)
    if not meta_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(fields)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


async def _download_bytes(url: str) -> bytes:
    """Lädt URL herunter, gibt Bytes zurück."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _resolve_local_path_from_url(url: str) -> Path | None:
    """
    Prüft ob URL auf lokale Static-Datei zeigt (z.B. /static/bgremoval/X.png).
    Gibt lokalen Pfad zurück oder None.
    """
    if "/static/bgremoval/" in url:
        # http://localhost:8000/static/bgremoval/{job_id}.png oder /static/bgremoval/...
        parts = url.rstrip("/").split("/")
        if parts:
            filename = parts[-1]
            if filename:
                path = BGREMOVAL_STORAGE_PATH / filename
                if path.exists():
                    return path
    return None


async def persist_image_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    prompt: str,
    result_url: str,
    negative_prompt: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """
    Speichert Bild-Job-Output im Asset-Ordner.
    Lädt Bild von result_url herunter (PicsArt/extern).
    """
    try:
        image_bytes = await _download_bytes(result_url)
    except Exception as e:
        logger.warning("Bild-Download für Asset fehlgeschlagen: %s", e)
        return

    step_data: dict[str, Any] = {
        "job_id": job_id,
        "provider_key": provider_key,
        "prompt": prompt,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if negative_prompt:
        step_data["negative_prompt"] = negative_prompt
    if width is not None:
        step_data["width"] = width
    if height is not None:
        step_data["height"] = height

    await update_step(
        asset_id,
        "image",
        step_data,
        file_bytes=image_bytes,
        filename="image_original.png",
    )
    logger.info("Asset %s: image step persisted", asset_id)


async def persist_bgremoval_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    source_file: str,
    result_url: str,
) -> None:
    """
    Speichert BgRemoval-Job-Output im Asset-Ordner.
    Nutzt lokale Datei falls URL auf /static/bgremoval zeigt, sonst Download.
    """
    local_path = _resolve_local_path_from_url(result_url)
    if local_path:
        file_bytes = local_path.read_bytes()
    else:
        try:
            file_bytes = await _download_bytes(result_url)
        except Exception as e:
            logger.warning("BgRemoval-Download für Asset fehlgeschlagen: %s", e)
            return

    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await update_step(
        asset_id,
        "bgremoval",
        step_data,
        file_bytes=file_bytes,
        filename="image_bgremoved.png",
    )
    logger.info("Asset %s: bgremoval step persisted", asset_id)


async def persist_mesh_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    source_file: str,
    glb_file_path: str,
) -> None:
    """
    Speichert Mesh-Job-Output im Asset-Ordner.
    Kopiert GLB von MESH_STORAGE_PATH.
    """
    src = Path(glb_file_path)
    if not src.exists():
        logger.warning("GLB-Datei nicht gefunden: %s", glb_file_path)
        return

    file_bytes = src.read_bytes()
    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await update_step(
        asset_id,
        "mesh",
        step_data,
        file_bytes=file_bytes,
        filename="mesh.glb",
    )
    logger.info("Asset %s: mesh step persisted", asset_id)


async def persist_rigging_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    source_file: str,
    glb_file_path: str,
) -> None:
    """
    Speichert Rigging-Job-Output im Asset-Ordner.
    Kopiert rigged GLB nach mesh_rigged.glb.
    """
    src = Path(glb_file_path)
    if not src.exists():
        logger.warning("Rigged GLB nicht gefunden: %s", glb_file_path)
        return

    file_bytes = src.read_bytes()
    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await update_step(
        asset_id,
        "rigging",
        step_data,
        file_bytes=file_bytes,
        filename="mesh_rigged.glb",
    )
    logger.info("Asset %s: rigging step persisted", asset_id)


async def persist_animation_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    motion_prompt: str,
    source_file: str,
    animated_bytes: bytes,
    filename: str = "mesh_animated.glb",
) -> None:
    """
    Speichert Animation-Job-Output im Asset-Ordner.
    filename: mesh_animated.glb oder mesh_animated.fbx (je nach Provider-Ausgabe).
    """
    step_data: dict[str, Any] = {
        "job_id": job_id,
        "provider_key": provider_key,
        "motion_prompt": motion_prompt,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await update_step(
        asset_id,
        "animation",
        step_data,
        file_bytes=animated_bytes,
        filename=filename,
    )
    logger.info("Asset %s: animation step persisted", asset_id)


def delete_asset(asset_id: str) -> bool:
    """
    Löscht Asset-Ordner mit allen Dateien.
    Gibt True zurück wenn gelöscht, False wenn nicht gefunden.
    Validiert asset_id als UUID, um Path-Traversal zu verhindern.
    """
    if not re.fullmatch(r"[0-9a-f-]{36}", asset_id):
        return False
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        return False
    shutil.rmtree(asset_path)
    logger.info("Asset %s gelöscht", asset_id)
    return True


def get_or_create_asset_id(existing_asset_id: str | None) -> str:
    """Gibt existing_asset_id zurück oder erstellt neues Asset."""
    if existing_asset_id and get_asset(existing_asset_id):
        return existing_asset_id
    return create_asset()


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
    asset_path = _asset_dir(asset_id)
    ext = Path(filename).suffix.lower() or ".png"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".png"
    target_filename = f"image_original{ext}"
    (asset_path / target_filename).write_bytes(file_bytes)

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

    meta_path = _metadata_path(asset_id)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["steps"]["image"] = step_data
    meta["source"] = "upload"
    meta["original_filename"] = filename
    meta["uploaded_at"] = now
    meta["updated_at"] = now
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
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
    asset_path = _asset_dir(asset_id)
    ext = Path(filename).suffix.lower()

    # Original behalten
    original_ext = ext or ".glb"
    original_filename = f"mesh_original{original_ext}"
    (asset_path / original_filename).write_bytes(file_bytes)

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
        except Exception as e:
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

        glb_bytes = mesh.export(file_type="glb")
        (asset_path / "mesh.glb").write_bytes(glb_bytes)

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

    meta_path = _metadata_path(asset_id)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["steps"]["mesh"] = step_data
    meta["source"] = "upload"
    meta["original_filename"] = filename
    meta["original_format"] = original_format
    meta["uploaded_at"] = now
    meta["updated_at"] = now
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return asset_id
