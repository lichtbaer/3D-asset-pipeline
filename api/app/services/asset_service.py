"""
Asset-Persistenz: Ordnerstruktur mit Metadaten für alle Pipeline-Outputs.
Jeder generierte Output wird auf dem Filesystem abgelegt.
Nutzt AssetPaths und MetadataService für zentralisierte Pfad- und Metadata-Logik.
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
)
from app.core.asset_paths import AssetPaths
from app.services.metadata_service import get_metadata_service

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
        image_processing: list[dict[str, Any]] | None = None,
        texture_baking: list[dict[str, Any]] | None = None,
        sketchfab_upload: dict[str, Any] | None = None,
        source: str | None = None,
        sketchfab_uid: str | None = None,
        sketchfab_url: str | None = None,
        sketchfab_author: str | None = None,
        downloaded_at: str | None = None,
        exports: list[dict[str, Any]] | None = None,
        deleted_at: str | None = None,
        name: str | None = None,
        tags: list[str] | None = None,
        rating: int | None = None,
        notes: str | None = None,
        favorited: bool | None = None,
    ):
        self.asset_id = asset_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.steps = steps
        self.processing = processing or []
        self.image_processing = image_processing or []
        self.texture_baking = texture_baking or []
        self.sketchfab_upload = sketchfab_upload
        self.source = source
        self.sketchfab_uid = sketchfab_uid
        self.sketchfab_url = sketchfab_url
        self.sketchfab_author = sketchfab_author
        self.downloaded_at = downloaded_at
        self.exports = exports or []
        self.deleted_at = deleted_at
        self.name = name
        self.tags = tags or []
        self.rating = rating
        self.notes = notes
        self.favorited = favorited or False

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "asset_id": self.asset_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": self.steps,
            "processing": self.processing,
            "image_processing": self.image_processing,
            "texture_baking": self.texture_baking,
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
        if self.deleted_at is not None:
            out["deleted_at"] = self.deleted_at
        if self.name is not None:
            out["name"] = self.name
        if self.tags:
            out["tags"] = self.tags
        if self.rating is not None:
            out["rating"] = self.rating
        if self.notes is not None:
            out["notes"] = self.notes
        if self.favorited is not None:
            out["favorited"] = self.favorited
        return out


def create_asset() -> str:
    """
    Legt Ordner + leere metadata.json an, gibt asset_id zurück.
    """
    asset_id = str(uuid.uuid4())
    paths = AssetPaths(asset_id)
    paths.base.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": {},
    }
    get_metadata_service().write(asset_id, metadata)
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
    paths = AssetPaths(asset_id)
    if not paths.base.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")

    if file_bytes is not None and filename:
        target = paths.processing_file(filename)
        await asyncio.to_thread(target.write_bytes, file_bytes)
        data["file"] = filename

    await asyncio.to_thread(
        get_metadata_service().mark_step_done, asset_id, step, data
    )


def get_asset(asset_id: str) -> AssetMetadata | None:
    """Liest metadata.json, gibt None wenn nicht vorhanden."""
    data = get_metadata_service().read(asset_id)
    if not data:
        return None
    return AssetMetadata(
        asset_id=data["asset_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        steps=data.get("steps", {}),
        processing=data.get("processing", []),
        image_processing=data.get("image_processing", []),
        texture_baking=data.get("texture_baking", []),
        sketchfab_upload=data.get("sketchfab_upload"),
        source=data.get("source"),
        sketchfab_uid=data.get("sketchfab_uid"),
        sketchfab_url=data.get("sketchfab_url"),
        sketchfab_author=data.get("sketchfab_author"),
        downloaded_at=data.get("downloaded_at"),
        exports=data.get("exports", []),
        deleted_at=data.get("deleted_at"),
        name=data.get("name"),
        tags=data.get("tags", []),
        rating=data.get("rating"),
        notes=data.get("notes"),
        favorited=data.get("favorited", False),
    )


def _get_search_text(meta: AssetMetadata) -> str:
    """Volltext für Suche: Name + Prompt + Tags."""
    parts: list[str] = []
    if meta.name:
        parts.append(meta.name.lower())
    for step_data in meta.steps.values():
        if isinstance(step_data, dict):
            for key in ("prompt", "motion_prompt"):
                if key in step_data and step_data[key]:
                    parts.append(str(step_data[key]).lower())
    parts.extend(t.lower() for t in meta.tags)
    return " ".join(parts)


def _matches_filters(
    meta: AssetMetadata,
    search: str | None,
    tags_filter: list[str],
    rating_min: int | None,
    has_step: str | None,
    favorited: bool | None,
    source: str | None,
) -> bool:
    """Prüft ob Asset alle Filter erfüllt."""
    if search:
        search_lower = search.lower().strip()
        if search_lower and search_lower not in _get_search_text(meta):
            return False
    if tags_filter:
        meta_tags_lower = {t.lower() for t in meta.tags}
        for t in tags_filter:
            if t.lower() not in meta_tags_lower:
                return False
    if rating_min is not None:
        r = meta.rating if meta.rating is not None else 0
        if r < rating_min:
            return False
    if has_step:
        if has_step not in meta.steps or not meta.steps.get(has_step):
            return False
    if favorited is not None and meta.favorited != favorited:
        return False
    if source and meta.source != source:
        return False
    return True


def list_assets(
    include_deleted: bool = False,
    search: str | None = None,
    tags: str | None = None,
    rating: int | None = None,
    has_step: str | None = None,
    favorited: bool | None = None,
    source: str | None = None,
    sort: str = "created_desc",
) -> list[AssetMetadata]:
    """Alle Assets mit optionalen Filtern und Sortierung. Ohne include_deleted
    werden soft-deleted Assets ausgelassen."""
    ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    assets: list[AssetMetadata] = []
    for path in ASSETS_STORAGE_PATH.iterdir():
        if path.is_dir():
            meta = get_asset(path.name)
            if meta:
                if include_deleted or not meta.deleted_at:
                    assets.append(meta)

    tags_filter = [t.strip() for t in (tags or "").split(",") if t.strip()]
    rating_min = rating if rating is not None else None

    assets = [
        a
        for a in assets
        if _matches_filters(
            a, search, tags_filter, rating_min, has_step, favorited, source
        )
    ]

    if sort == "created_asc":
        assets.sort(key=lambda a: a.created_at)
    elif sort == "name":
        assets.sort(
            key=lambda a: (a.name or "").lower() or a.asset_id.lower()
        )
    elif sort == "rating":
        assets.sort(
            key=lambda a: (a.rating if a.rating is not None else 0),
            reverse=True,
        )
    else:
        assets.sort(key=lambda a: a.created_at, reverse=True)
    return assets


def get_all_tags() -> list[str]:
    """Alle verwendeten Tags im System (für Autocomplete)."""
    ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for path in ASSETS_STORAGE_PATH.iterdir():
        if path.is_dir():
            meta = get_asset(path.name)
            if meta and meta.tags:
                for t in meta.tags:
                    if t.strip():
                        seen.add(t.strip())
    return sorted(seen)


def update_asset_meta(
    asset_id: str,
    name: str | None = None,
    tags: list[str] | None = None,
    rating: int | None = None,
    notes: str | None = None,
    favorited: bool | None = None,
) -> None:
    """Aktualisiert Meta-Felder (Name, Tags, Rating, Notes, Favorit). Partial update."""
    fields: dict[str, Any] = {}
    if name is not None:
        fields["name"] = name
    if tags is not None:
        fields["tags"] = tags
    if rating is not None:
        fields["rating"] = rating
    if notes is not None:
        fields["notes"] = notes
    if favorited is not None:
        fields["favorited"] = favorited
    if fields:
        get_metadata_service().update(asset_id, **fields)


# Original-Files, die nicht via DELETE /files/{filename} löschbar sind
PROTECTED_FILENAMES = frozenset({"mesh.glb", "image_bgremoved.png"})


def _is_protected_file(meta: AssetMetadata, filename: str) -> bool:
    """Prüft ob Datei ein Original-Output ist (nur via Asset-Löschung entfernbar)."""
    if filename in PROTECTED_FILENAMES:
        return True
    # image_original.* (image step)
    if filename.startswith("image_original."):
        return True
    if "image" in meta.steps and meta.steps["image"].get("file") == filename:
        return True
    if "bgremoval" in meta.steps and meta.steps["bgremoval"].get("file") == filename:
        return True
    if "mesh" in meta.steps and meta.steps["mesh"].get("file") == filename:
        return True
    return False


# Step-Abhängigkeiten: step -> steps die davon abhängen
STEP_DEPENDENCIES: dict[str, list[str]] = {
    "image": ["bgremoval", "mesh", "rigging", "animation"],
    "bgremoval": ["mesh", "rigging", "animation"],
    "mesh": ["rigging", "animation"],
    "rigging": ["animation"],
    "animation": [],
}


def get_dependent_steps(step: str, existing_steps: set[str]) -> list[str]:
    """Gibt Steps zurück, die von step abhängen und existieren."""
    downstream = STEP_DEPENDENCIES.get(step, [])
    return [s for s in downstream if s in existing_steps]


def delete_asset_file(asset_id: str, filename: str) -> bool:
    """
    Löscht einzelne Datei aus Asset-Ordner und bereinigt metadata.json.
    Entfernt Einträge aus processing, image_processing oder exports.
    Gibt True zurück wenn erfolgreich.
    Wirft PermissionError wenn Original-File (mesh.glb, image.png, image_bgremoved.png).
    """
    meta = get_asset(asset_id)
    if not meta:
        raise FileNotFoundError(f"Asset {asset_id} nicht gefunden")
    if _is_protected_file(meta, filename):
        raise PermissionError(
            f"Original-Datei {filename} kann nicht einzeln gelöscht werden. "
            "Nutze Asset-Löschung."
        )

    path = get_file_path(asset_id, filename)
    if not path:
        raise FileNotFoundError(f"Datei {filename} nicht in Asset {asset_id}")

    meta_dict = get_metadata_service().read(asset_id)
    if not meta_dict:
        raise FileNotFoundError(f"Asset {asset_id} nicht gefunden")
    changed = False

    # Processing-Einträge entfernen
    if "processing" in meta_dict:
        before = len(meta_dict["processing"])
        meta_dict["processing"] = [
            e for e in meta_dict["processing"]
            if e.get("output_file") != filename
        ]
        if len(meta_dict["processing"]) < before:
            changed = True

    # Image-Processing-Einträge entfernen
    if "image_processing" in meta_dict:
        before = len(meta_dict["image_processing"])
        meta_dict["image_processing"] = [
            e for e in meta_dict["image_processing"]
            if e.get("output_file") != filename
        ]
        if len(meta_dict["image_processing"]) < before:
            changed = True

    # Export-Einträge entfernen (GLTF hat .gltf + .bin)
    if "exports" in meta_dict:
        to_remove: list[int] = []
        for i, e in enumerate(meta_dict["exports"]):
            out = e.get("output_file", "")
            if out == filename:
                to_remove.append(i)
            elif out == filename.replace(".bin", ".gltf"):
                to_remove.append(i)
        for i in reversed(to_remove):
            meta_dict["exports"].pop(i)
            changed = True

    # Datei(en) löschen
    path.unlink(missing_ok=True)
    # GLTF: .gltf und .bin gehören zusammen
    if filename.endswith(".gltf"):
        bin_path = path.with_suffix(".bin")
        if bin_path.exists():
            bin_path.unlink(missing_ok=True)
    elif filename.endswith(".bin"):
        gltf_path = path.with_suffix(".gltf")
        if gltf_path.exists():
            gltf_path.unlink(missing_ok=True)

    if changed:
        meta_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        get_metadata_service().write(asset_id, meta_dict)

    logger.info("Asset %s: Datei %s gelöscht", asset_id, filename)
    return True


def delete_step(
    asset_id: str,
    step_name: str,
    cascade: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """
    Löscht kompletten Pipeline-Step. Entfernt Step-Datei(en) und metadata.
    Wenn force=False und abhängige Steps existieren: gibt requires_confirmation zurück.
    Wenn cascade=True: löscht auch abhängige Steps.
    """
    valid_steps = {"image", "bgremoval", "mesh", "rigging", "animation"}
    if step_name not in valid_steps:
        raise ValueError(f"Ungültiger Step: {step_name}")

    meta = get_asset(asset_id)
    if not meta:
        raise FileNotFoundError(f"Asset {asset_id} nicht gefunden")

    existing = {s for s in valid_steps if s in meta.steps and meta.steps[s]}
    dependent = get_dependent_steps(step_name, existing)

    if not force and dependent and not cascade:
        return {
            "requires_confirmation": True,
            "affected_steps": dependent,
            "message": f"{', '.join(dependent)} basieren auf diesem Step. "
            "Mit cascade=true werden alle gelöscht.",
        }

    steps_to_delete = [step_name]
    if cascade:
        steps_to_delete = [step_name] + dependent

    meta_dict = get_metadata_service().read(asset_id)
    if not meta_dict:
        raise FileNotFoundError(f"Asset {asset_id} nicht gefunden")
    asset_path = AssetPaths(asset_id).base

    for step in steps_to_delete:
        if step not in meta_dict.get("steps", {}):
            continue
        step_data = meta_dict["steps"][step]
        step_file = step_data.get("file")
        if step_file:
            file_path = asset_path / step_file
            if file_path.exists():
                file_path.unlink(missing_ok=True)
        del meta_dict["steps"][step]

    meta_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    get_metadata_service().write(asset_id, meta_dict)
    logger.info("Asset %s: Steps %s gelöscht", asset_id, steps_to_delete)
    return {"requires_confirmation": False, "affected_steps": [], "message": ""}


def get_file_path(asset_id: str, filename: str) -> Path | None:
    """Pfad zur Datei, None wenn nicht vorhanden oder Pfad ungültig.

    Validiert asset_id als UUID und verhindert Path-Traversal-Angriffe.
    """
    if not re.fullmatch(r"[0-9a-f-]{36}", asset_id):
        return None
    base = AssetPaths(asset_id).base.resolve()
    target = (base / filename).resolve()
    if not target.is_relative_to(base):
        return None
    return target if target.is_file() else None


def get_asset_dir(asset_id: str) -> Path:
    """Asset-Ordner-Pfad. Erstellt nicht automatisch."""
    return AssetPaths(asset_id).base


def write_asset_file(asset_id: str, filename: str, data: bytes) -> None:
    """Schreibt Datei in Asset-Ordner."""
    paths = AssetPaths(asset_id)
    if not paths.base.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    paths.processing_file(filename).write_bytes(data)


def list_mesh_files(asset_id: str) -> list[str]:
    """Listet alle GLB-Dateien im Asset-Ordner (für Mesh-Processing-Quelle)."""
    paths = AssetPaths(asset_id)
    if not paths.base.exists():
        return []
    return sorted(
        f.name
        for f in paths.base.iterdir()
        if f.is_file() and f.suffix.lower() == ".glb"
    )


def append_processing_entry(asset_id: str, entry: dict[str, Any]) -> None:
    """Fügt Eintrag zum processing-Array in metadata.json hinzu."""
    get_metadata_service().add_processing_entry(asset_id, entry)


def append_image_processing_entry(asset_id: str, entry: dict[str, Any]) -> None:
    """Fügt Eintrag zum image_processing-Array in metadata.json hinzu."""
    get_metadata_service().add_image_processing_entry(asset_id, entry)


def append_texture_baking_entry(asset_id: str, entry: dict[str, Any]) -> None:
    """Fügt Eintrag zum texture_baking-Array in metadata.json hinzu."""
    get_metadata_service().add_texture_baking_entry(asset_id, entry)


def list_image_files(asset_id: str) -> list[str]:
    """Listet alle Bild-Dateien im Asset-Ordner (PNG, JPG, WebP)."""
    paths = AssetPaths(asset_id)
    if not paths.base.exists():
        return []
    return sorted(
        f.name
        for f in paths.base.iterdir()
        if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    )


def update_metadata_fields(asset_id: str, fields: dict[str, Any]) -> None:
    """Aktualisiert Top-Level-Felder in metadata.json (z.B. sketchfab_upload, source)."""
    get_metadata_service().update(asset_id, **fields)


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


def soft_delete_asset(asset_id: str) -> bool:
    """
    Soft-Delete: Setzt deleted_at in metadata.json.
    Gibt True zurück wenn erfolgreich.
    """
    meta = get_asset(asset_id)
    if not meta:
        return False
    update_metadata_fields(
        asset_id,
        {"deleted_at": datetime.now(timezone.utc).isoformat()},
    )
    logger.info("Asset %s in Papierkorb verschoben", asset_id)
    return True


def restore_asset(asset_id: str) -> bool:
    """
    Stellt soft-deleted Asset wieder her (setzt deleted_at auf null).
    """
    meta = get_asset(asset_id)
    if not meta:
        return False
    if not meta.deleted_at:
        return True  # Bereits aktiv
    meta_dict = get_metadata_service().read(asset_id)
    meta_dict.pop("deleted_at", None)
    meta_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    get_metadata_service().write(asset_id, meta_dict)
    logger.info("Asset %s wiederhergestellt", asset_id)
    return True


def delete_asset(asset_id: str, permanent: bool = False) -> bool:
    """
    Soft-Delete (permanent=False): Setzt deleted_at, Ordner bleibt.
    Permanent (permanent=True): Löscht Asset-Ordner mit allen Dateien.
    Gibt True zurück wenn gelöscht, False wenn nicht gefunden.
    Validiert asset_id als UUID, um Path-Traversal zu verhindern.
    """
    if not re.fullmatch(r"[0-9a-f-]{36}", asset_id):
        return False
    asset_path = AssetPaths(asset_id).base
    if not asset_path.exists():
        return False
    if permanent:
        shutil.rmtree(asset_path)
        logger.info("Asset %s permanent gelöscht", asset_id)
    else:
        soft_delete_asset(asset_id)
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
