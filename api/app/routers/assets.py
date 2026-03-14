"""Asset-API: persistente Speicherung von Pipeline-Outputs."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.asset import (
    AssetDetailResponse,
    AssetListItem,
    AssetStepInfo,
    CreateAssetResponse,
)
from app.schemas.mesh_processing import (
    ClipFloorRequest,
    MeshAnalysis,
    RemoveComponentsRequest,
    RepairRequest,
    SimplifyRequest,
)
from app.services import asset_service
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
    }


def _thumbnail_url(meta: asset_service.AssetMetadata) -> str | None:
    """Erste verfügbare Bild-URL für Thumbnail."""
    if "image" in meta.steps and meta.steps["image"].get("file"):
        return f"/assets/{meta.asset_id}/files/{meta.steps['image']['file']}"
    if "bgremoval" in meta.steps and meta.steps["bgremoval"].get("file"):
        return f"/assets/{meta.asset_id}/files/{meta.steps['bgremoval']['file']}"
    return None


@router.get("", response_model=list[AssetListItem])
async def list_assets():
    """Liste aller Assets, sortiert nach created_at desc."""
    assets = asset_service.list_assets()
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
        )
        for a in assets
    ]


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
    """Static-File-Download für Asset-Dateien (Bild, GLB)."""
    path = asset_service.get_file_path(asset_id, filename)
    if not path:
        raise HTTPException(404, detail="Datei nicht gefunden")

    # Content-Type je nach Extension
    suffix = Path(filename).suffix.lower()
    media_types: dict[str, str] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".glb": "model/gltf-binary",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(path, media_type=media_type)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: str):
    """Löscht Asset-Ordner und alle zugehörigen Dateien unwiderruflich."""
    deleted = asset_service.delete_asset(asset_id)
    if not deleted:
        raise HTTPException(404, detail="Asset nicht gefunden")


@router.post("", response_model=CreateAssetResponse)
async def create_asset():
    """Neues Asset anlegen, gibt asset_id zurück."""
    asset_id = asset_service.create_asset()
    return CreateAssetResponse(asset_id=asset_id)
