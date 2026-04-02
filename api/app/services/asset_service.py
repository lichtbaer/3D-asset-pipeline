"""
Asset-Persistenz: Ordnerstruktur mit Metadaten für alle Pipeline-Outputs.
Jeder generierte Output wird auf dem Filesystem abgelegt.
Nutzt AssetPaths und MetadataService für zentralisierte Pfad- und Metadata-Logik.
"""

import asyncio
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config.storage import ASSETS_STORAGE_PATH
from app.core.asset_paths import AssetPaths
from app.services.metadata_service import get_metadata_service

logger = logging.getLogger(__name__)

# Step-Typen fuer metadata.json
StepType = str  # "image" | "bgremoval" | "mesh"

# Felder die immer in to_dict() enthalten sind
_ALWAYS_INCLUDE = frozenset({
    "asset_id", "created_at", "updated_at", "steps",
    "processing", "image_processing", "texture_baking", "exports",
})


class AssetMetadata(BaseModel):
    """Repraesentation der metadata.json eines Assets."""

    model_config = {"populate_by_name": True}

    asset_id: str
    created_at: str
    updated_at: str
    steps: dict[str, dict[str, Any]] = Field(default_factory=dict)
    processing: list[dict[str, Any]] = Field(default_factory=list)
    image_processing: list[dict[str, Any]] = Field(default_factory=list)
    texture_baking: list[dict[str, Any]] = Field(default_factory=list)
    exports: list[dict[str, Any]] = Field(default_factory=list)
    sketchfab_upload: dict[str, Any] | None = None
    source: str | None = None
    sketchfab_uid: str | None = None
    sketchfab_url: str | None = None
    sketchfab_author: str | None = None
    downloaded_at: str | None = None
    deleted_at: str | None = None
    name: str | None = None
    tags: list[str] = Field(default_factory=list)
    rating: int | None = None
    notes: str | None = None
    favorited: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialisiert fuer metadata.json — optionale Felder nur wenn gesetzt."""
        full = self.model_dump()
        out: dict[str, Any] = {k: v for k, v in full.items() if k in _ALWAYS_INCLUDE}
        for key, value in full.items():
            if key in _ALWAYS_INCLUDE:
                continue
            # tags: nur wenn nicht-leer
            if key == "tags":
                if value:
                    out[key] = value
            # favorited: immer wenn True (bool-Default ist False)
            elif key == "favorited":
                if value:
                    out[key] = value
            # alle anderen: nur wenn nicht None
            elif value is not None:
                out[key] = value
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
    return AssetMetadata(**data)


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


# --- Re-exports from asset_persistence for backwards compatibility ---
from app.services.asset_persistence import (  # noqa: E402, F401
    persist_animation_job,
    persist_bgremoval_job,
    persist_image_job,
    persist_mesh_job,
    persist_rigging_job,
)


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
        # Audit-Log: Dateien und Gesamtgröße erfassen vor dem Löschen
        files: list[str] = []
        total_size = 0
        for f in asset_path.rglob("*"):
            if f.is_file():
                files.append(f.name)
                total_size += f.stat().st_size
        logger.info(
            "Asset %s permanent gelöscht — %d Dateien, %.2f MB (%s)",
            asset_id,
            len(files),
            total_size / (1024 * 1024),
            ", ".join(files[:10]) + ("..." if len(files) > 10 else ""),
        )
        shutil.rmtree(asset_path)
    else:
        soft_delete_asset(asset_id)
    return True


def get_or_create_asset_id(existing_asset_id: str | None) -> str:
    """Gibt existing_asset_id zurück oder erstellt neues Asset."""
    if existing_asset_id and get_asset(existing_asset_id):
        return existing_asset_id
    return create_asset()


def duplicate_asset(asset_id: str, up_to_step: str | None = None) -> tuple[str, list[str]]:
    """
    Klont ein Asset in einen neuen Asset-Ordner.

    Kopiert alle Dateien und metadata.json. Das neue Asset erhält eine frische asset_id
    und aktuelle Timestamps. Tags, Notes, Name und Rating werden übernommen.

    Args:
        asset_id: Quell-Asset-ID
        up_to_step: Optional — nur Schritte bis (einschließlich) dieses Schritt kopieren.
                    z.B. "mesh" kopiert nur image/bgremoval/mesh, nicht rigging/animation.

    Returns:
        (new_asset_id, copied_steps) — neue asset_id und Liste der kopierten Steps
    """
    src_meta = get_asset(asset_id)
    if not src_meta:
        raise FileNotFoundError(f"Asset {asset_id} nicht gefunden")

    src_dir = AssetPaths(asset_id).base
    if not src_dir.exists():
        raise FileNotFoundError(f"Asset-Ordner {asset_id} nicht gefunden")

    new_asset_id = create_asset()
    dst_dir = AssetPaths(new_asset_id).base

    # Pipeline-Step-Reihenfolge für up_to_step-Filter
    step_order = ["image", "bgremoval", "mesh", "rigging", "animation"]

    if up_to_step and up_to_step in step_order:
        cutoff = step_order.index(up_to_step)
        allowed_steps = set(step_order[: cutoff + 1])
    else:
        allowed_steps = None

    copied_steps: list[str] = []

    # Alle Dateien kopieren (außer metadata.json — wird neu geschrieben)
    for src_file in src_dir.iterdir():
        if not src_file.is_file() or src_file.name == "metadata.json":
            continue
        shutil.copy2(src_file, dst_dir / src_file.name)

    # metadata.json neu aufbauen: frische IDs, gefilterte Steps
    now = datetime.now(timezone.utc).isoformat()
    new_meta: dict[str, Any] = {
        "asset_id": new_asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": {},
        "processing": [],
        "image_processing": [],
        "texture_baking": [],
        "exports": [],
    }

    for step_name, step_data in src_meta.steps.items():
        if allowed_steps is not None and step_name not in allowed_steps:
            continue
        new_meta["steps"][step_name] = dict(step_data)
        copied_steps.append(step_name)

    # Optionale Metadaten übernehmen
    if src_meta.name:
        new_meta["name"] = f"{src_meta.name} (Kopie)"
    if src_meta.tags:
        new_meta["tags"] = list(src_meta.tags)
    if src_meta.notes:
        new_meta["notes"] = src_meta.notes
    if src_meta.rating is not None:
        new_meta["rating"] = src_meta.rating
    if src_meta.processing and allowed_steps is None:
        new_meta["processing"] = list(src_meta.processing)

    get_metadata_service().write(new_asset_id, new_meta)
    logger.info(
        "Asset %s dupliziert → %s (Steps: %s)",
        asset_id,
        new_asset_id,
        copied_steps,
    )
    return new_asset_id, copied_steps


# --- Re-exports from asset_import for backwards compatibility ---
from app.services.asset_import import (  # noqa: E402, F401
    create_asset_from_image_upload,
    create_asset_from_mesh_upload,
)
