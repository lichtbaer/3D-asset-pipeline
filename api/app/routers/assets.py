"""Asset-API: persistente Speicherung von Pipeline-Outputs."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.schemas.asset import (
    AssetDetailResponse,
    AssetListItem,
    AssetMetaUpdateRequest,
    BatchDeleteRequest,
    CreateAssetResponse,
    ExportListItem,
    ExportRequest,
    ExportResponse,
    ExportsListResponse,
    AssetStepInfo,
    SketchfabUploadInfo,
    UploadAssetResponse,
)
from app.schemas.mesh_processing import (
    ClipFloorRequest,
    MeshAnalysis,
    RemoveComponentsRequest,
    RepairRequest,
    SimplifyRequest,
)
from app.services import asset_service
from app.services.mesh_export_service import export as mesh_export, list_exports
from app.services.mesh_processing_service import (
    analyze as mesh_analyze,
    clip_floor as mesh_clip_floor,
    repair as mesh_repair,
    remove_small_components as mesh_remove_components,
    simplify as mesh_simplify,
)

router = APIRouter(prefix="/assets", tags=["assets"])


def _step_to_info(step_data: dict) -> dict:
    """Konvertiert Step-Dict zu AssetStepInfo-kompatiblem Dict."""
    return {
        "job_id": str(step_data.get("job_id", "")),
        "provider_key": step_data.get("provider_key", ""),
        "file": step_data.get("file", ""),
        "generated_at": step_data.get("generated_at"),
        "name": step_data.get("name"),
    }


def _thumbnail_url(meta: asset_service.AssetMetadata) -> str | None:
    """Erste verfügbare Bild-URL für Thumbnail."""
    if "image" in meta.steps and meta.steps["image"].get("file"):
        return f"/assets/{meta.asset_id}/files/{meta.steps['image']['file']}"
    if "bgremoval" in meta.steps and meta.steps["bgremoval"].get("file"):
        return f"/assets/{meta.asset_id}/files/{meta.steps['bgremoval']['file']}"
    return None


@router.get("/tags")
async def get_asset_tags():
    """Alle verwendeten Tags im System (für Autocomplete)."""
    tags = asset_service.get_all_tags()
    return {"tags": tags}


@router.get("", response_model=list[AssetListItem])
async def list_assets(
    include_deleted: bool = Query(False, description="Papierkorb-Assets einbeziehen"),
    search: str | None = Query(None, description="Volltextsuche in Name + Prompt + Tags"),
    tags: str | None = Query(None, description="Komma-getrennte Tags (Asset muss ALLE haben)"),
    rating: int | None = Query(None, ge=1, le=5, description="Mindest-Rating 1-5"),
    has_step: str | None = Query(
        None,
        description="Filter: image, mesh, rigging, animation",
    ),
    favorited: bool | None = Query(None, description="Nur Favoriten"),
    source: str | None = Query(
        None,
        description="Filter: generated, upload, sketchfab",
    ),
    sort: str = Query(
        "created_desc",
        description="created_desc, created_asc, name, rating",
    ),
):
    """Liste aller Assets mit Filtern und Sortierung."""
    if has_step and has_step not in ("image", "mesh", "rigging", "animation"):
        raise HTTPException(400, detail="has_step muss image, mesh, rigging oder animation sein")
    if sort and sort not in ("created_desc", "created_asc", "name", "rating"):
        raise HTTPException(400, detail="sort muss created_desc, created_asc, name oder rating sein")

    assets = asset_service.list_assets(
        include_deleted=include_deleted,
        search=search,
        tags=tags,
        rating=rating,
        has_step=has_step,
        favorited=favorited,
        source=source,
        sort=sort or "created_desc",
    )
    return [
        AssetListItem(
            asset_id=a.asset_id,
            created_at=a.created_at,
            updated_at=a.updated_at,
            steps={
                k: AssetStepInfo(**_step_to_info(v))
                for k, v in a.steps.items()
            },
            thumbnail_url=_thumbnail_url(a),
            deleted_at=a.deleted_at,
            name=a.name,
            tags=a.tags,
            rating=a.rating,
            favorited=a.favorited,
        )
        for a in assets
    ]


def _to_sketchfab_upload_info(
    d: dict | None,
) -> SketchfabUploadInfo | None:
    """Konvertiert sketchfab_upload-Dict zu Schema."""
    if not d or not isinstance(d, dict):
        return None
    uid = d.get("uid")
    url = d.get("url")
    if not uid or not url:
        return None
    return SketchfabUploadInfo(
        uid=str(uid),
        url=str(url),
        embed_url=str(d.get("embed_url", "")),
        uploaded_at=str(d.get("uploaded_at", "")),
        is_private=bool(d.get("is_private", False)),
    )


# Upload-Endpunkte (vor /{asset_id} definieren)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
MESH_EXTENSIONS = {".glb", ".gltf", ".obj", ".ply", ".stl", ".zip"}
MESH_MAX_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post("/upload/image", response_model=UploadAssetResponse)
async def upload_image(
    file: UploadFile = File(...),
    name: str | None = Form(None),
):
    """Bild hochladen (JPG, PNG, WebP, max. 20 MB). Erstellt Asset mit steps.image."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"Ungültiges Format. Erlaubt: {', '.join(IMAGE_EXTENSIONS)}",
        )
    content = await file.read()
    if len(content) > IMAGE_MAX_BYTES:
        raise HTTPException(
            400,
            detail=f"Datei zu groß. Maximum: {IMAGE_MAX_BYTES // (1024*1024)} MB",
        )
    target_ext = ext if ext in IMAGE_EXTENSIONS else ".png"
    target_filename = f"image_original{target_ext}"
    asset_id = asset_service.create_asset_from_image_upload(
        content, file.filename or "image" + ext, name
    )
    return UploadAssetResponse(asset_id=asset_id, file=target_filename)


@router.post("/upload/mesh", response_model=UploadAssetResponse)
async def upload_mesh(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    mtl_file: UploadFile | None = File(None),
):
    """3D-Modell hochladen (GLB, GLTF, OBJ, PLY, STL, ZIP; max. 100 MB). Konvertiert zu GLB."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in MESH_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"Ungültiges Format. Erlaubt: {', '.join(MESH_EXTENSIONS)}",
        )
    content = await file.read()
    if len(content) > MESH_MAX_BYTES:
        raise HTTPException(
            400,
            detail=f"Datei zu groß. Maximum: {MESH_MAX_BYTES // (1024*1024)} MB",
        )
    mtl_bytes: bytes | None = None
    mtl_filename: str | None = None
    if mtl_file and mtl_file.filename:
        mtl_ext = Path(mtl_file.filename).suffix.lower()
        if mtl_ext == ".mtl":
            mtl_bytes = await mtl_file.read()
            mtl_filename = Path(mtl_file.filename).name
    try:
        asset_id = asset_service.create_asset_from_mesh_upload(
            content,
            file.filename or "mesh" + ext,
            name,
            mtl_bytes=mtl_bytes,
            mtl_filename=mtl_filename,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
    return UploadAssetResponse(asset_id=asset_id, file="mesh.glb")


@router.patch("/{asset_id}/meta")
async def patch_asset_meta(asset_id: str, body: AssetMetaUpdateRequest):
    """Asset-Metadaten aktualisieren (Name, Tags, Rating, Notes, Favorit). Partial update."""
    meta = asset_service.get_asset(asset_id)
    if not meta:
        raise HTTPException(404, detail="Asset nicht gefunden")
    updates: dict[str, object] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.tags is not None:
        updates["tags"] = body.tags
    if body.rating is not None:
        updates["rating"] = body.rating
    if body.notes is not None:
        updates["notes"] = body.notes
    if body.favorited is not None:
        updates["favorited"] = body.favorited
    if not updates:
        return {"message": "Keine Änderungen"}
    asset_service.update_asset_meta(
        asset_id,
        name=body.name,
        tags=body.tags,
        rating=body.rating,
        notes=body.notes,
        favorited=body.favorited,
    )
    return {"message": "Metadaten aktualisiert"}


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset(asset_id: str):
    """Vollständige metadata.json eines Assets."""
    meta = asset_service.get_asset(asset_id)
    if not meta:
        raise HTTPException(404, detail="Asset nicht gefunden")
    return AssetDetailResponse(
        asset_id=meta.asset_id,
        created_at=meta.created_at,
        updated_at=meta.updated_at,
        steps=meta.steps,
        processing=meta.processing,
        sketchfab_upload=_to_sketchfab_upload_info(meta.sketchfab_upload),
        source=meta.source,
        sketchfab_uid=meta.sketchfab_uid,
        sketchfab_url=meta.sketchfab_url,
        sketchfab_author=meta.sketchfab_author,
        downloaded_at=meta.downloaded_at,
        exports=meta.exports,
        name=meta.name,
        tags=meta.tags,
        rating=meta.rating,
        notes=meta.notes,
        favorited=meta.favorited,
    )


@router.get("/{asset_id}/process/sources")
async def process_sources(asset_id: str):
    """Liste verfügbarer Mesh-Dateien (GLB) als Quellen für Processing."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    return {"sources": asset_service.list_mesh_files(asset_id)}


@router.get("/{asset_id}/process/analyze", response_model=MeshAnalysis)
async def process_analyze(asset_id: str, source_file: str = "mesh.glb"):
    """Mesh-Kennzahlen analysieren (kein neues File)."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    try:
        return mesh_analyze(asset_id, source_file)
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e


@router.post("/{asset_id}/process/simplify")
async def process_simplify(asset_id: str, body: SimplifyRequest):
    """Mesh vereinfachen, speichert mesh_simplified_{target_faces}.glb."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    try:
        output_file, entry = mesh_simplify(
            asset_id, body.source_file, body.target_faces
        )
        return {"output_file": output_file, "processing": entry}
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e


@router.post("/{asset_id}/process/repair")
async def process_repair(asset_id: str, body: RepairRequest):
    """Mesh reparieren, speichert mesh_repaired.glb."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    try:
        output_file, entry = mesh_repair(
            asset_id, body.source_file, body.operations
        )
        return {"output_file": output_file, "processing": entry}
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e


@router.post("/{asset_id}/process/clip-floor")
async def process_clip_floor(asset_id: str, body: ClipFloorRequest):
    """Boden unterhalb Y-Schwellwert abschneiden, speichert mesh_clipped.glb."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    try:
        _output_file, result = mesh_clip_floor(
            asset_id, body.source_file, body.y_threshold
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e


@router.post("/{asset_id}/process/remove-components")
async def process_remove_components(asset_id: str, body: RemoveComponentsRequest):
    """Kleine isolierte Komponenten entfernen, speichert mesh_cleaned.glb."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    try:
        _output_file, result = mesh_remove_components(
            asset_id,
            body.source_file,
            body.min_component_ratio,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e


@router.get("/{asset_id}/files/{filename}")
async def get_asset_file(asset_id: str, filename: str):
    """Static-File-Download für Asset-Dateien (Bild, GLB, Export-Formate)."""
    path = asset_service.get_file_path(asset_id, filename)
    if not path:
        raise HTTPException(404, detail="Datei nicht gefunden")

    # Content-Type je nach Extension
    suffix = Path(filename).suffix.lower()
    media_types: dict[str, str] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".glb": "model/gltf-binary",
        ".stl": "model/stl",
        ".obj": "text/plain",
        ".mtl": "text/plain",
        ".ply": "application/octet-stream",
        ".gltf": "model/gltf+json",
        ".bin": "application/octet-stream",
        ".zip": "application/zip",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(path, media_type=media_type)


@router.post("/{asset_id}/export", response_model=ExportResponse)
async def export_asset(asset_id: str, body: ExportRequest):
    """Mesh in Zielformat exportieren (STL, OBJ, PLY, GLTF)."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    try:
        result = await asyncio.to_thread(
            mesh_export,
            asset_id=asset_id,
            source_file=body.source_file,
            target_format=body.format,
        )
        return ExportResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e


@router.get("/{asset_id}/exports", response_model=ExportsListResponse)
async def get_asset_exports(asset_id: str):
    """Liste aller vorhandenen Exports des Assets."""
    if not asset_service.get_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden")
    exports = list_exports(asset_id)
    return ExportsListResponse(
        exports=[ExportListItem(**e) for e in exports]
    )


@router.delete("/batch", status_code=200)
async def delete_assets_batch(body: BatchDeleteRequest):
    """
    Mehrere Assets löschen. permanent=false: Soft-Delete (Papierkorb).
    permanent=true: Unwiderrufliches Löschen.
    Gibt Anzahl gelöschter Assets zurück.
    """
    deleted = 0
    for aid in body.asset_ids:
        if asset_service.delete_asset(aid, permanent=body.permanent):
            deleted += 1
    return {"deleted_count": deleted}


@router.post("/{asset_id}/restore", status_code=204)
async def restore_asset(asset_id: str):
    """Asset aus Papierkorb wiederherstellen."""
    if not asset_service.restore_asset(asset_id):
        raise HTTPException(404, detail="Asset nicht gefunden oder nicht gelöscht")


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: str, permanent: bool = False):
    """
    Soft-Delete (Standard): Asset in Papierkorb verschieben (deleted_at setzen).
    Permanent (permanent=true): Ordner und alle Dateien unwiderruflich löschen.
    """
    deleted = asset_service.delete_asset(asset_id, permanent=permanent)
    if not deleted:
        raise HTTPException(404, detail="Asset nicht gefunden")


@router.post("", response_model=CreateAssetResponse)
async def create_asset():
    """Neues Asset anlegen, gibt asset_id zurück."""
    asset_id = asset_service.create_asset()
    return CreateAssetResponse(asset_id=asset_id)
