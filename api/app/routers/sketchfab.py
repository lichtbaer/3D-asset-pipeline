"""Sketchfab-API: Upload zu Sketchfab, Import von Sketchfab."""

import json
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.errors import raise_api_error
from app.database import async_session_factory, get_session
from app.models import GenerationJob
from app.schemas.sketchfab import (
    SketchfabImportRequest,
    SketchfabImportResponse,
    SketchfabMeModelsResponse,
    SketchfabModelItem,
    SketchfabStatusResponse,
    SketchfabUploadRequest,
    SketchfabUploadResponse,
    SketchfabUploadStatusResponse,
)
from app.services import asset_service
from app.services.sketchfab_service import SketchfabService, SketchfabUploadResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["sketchfab"])


def _get_sketchfab_service() -> SketchfabService | None:
    """Liefert SketchfabService wenn Token gesetzt, sonst None."""
    token = os.getenv("SKETCHFAB_API_TOKEN", "").strip()
    if not token:
        return None
    return SketchfabService(token)


@router.get("/sketchfab/status", response_model=SketchfabStatusResponse)
async def sketchfab_status():
    """Feature-Flag: Sketchfab verfügbar wenn SKETCHFAB_API_TOKEN gesetzt."""
    return SketchfabStatusResponse(enabled=bool(_get_sketchfab_service()))


@router.post(
    "/assets/{asset_id}/sketchfab/upload",
    response_model=SketchfabUploadResponse,
    status_code=202,
)
async def upload_to_sketchfab(
    asset_id: str,
    body: SketchfabUploadRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Startet Upload-Job: Asset zu Sketchfab hochladen."""
    svc = _get_sketchfab_service()
    if not svc:
        raise_api_error(
            503,
            "Sketchfab nicht konfiguriert. SKETCHFAB_API_TOKEN in .env setzen.",
            code="SERVICE_UNAVAILABLE",
        )

    meta = asset_service.get_asset(asset_id)
    if not meta:
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")

    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise_api_error(404, "Ungültige Asset-ID", code="INVALID_ASSET_ID")

    # Prüfen ob GLB vorhanden
    path = asset_service.get_file_path(asset_id, body.source_file)
    if not path or not path.exists():
        raise_api_error(
            404,
            f"Datei {body.source_file} nicht im Asset. Verfügbar: {asset_service.list_mesh_files(asset_id)}",
            code="FILE_NOT_FOUND",
        )

    job = GenerationJob(
        job_type="sketchfab_upload",
        status="pending",
        prompt=json.dumps(
            {
                "source_file": body.source_file,
                "name": body.name,
                "description": body.description,
                "tags": body.tags,
                "is_private": body.is_private,
            }
        ),
        provider_key="sketchfab",
        asset_id=asset_uuid,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        _run_sketchfab_upload,
        str(job.id),
        asset_id,
        body.source_file,
        body.name,
        body.description,
        body.tags,
        body.is_private,
    )

    return SketchfabUploadResponse(job_id=str(job.id), status="pending")


async def _run_sketchfab_upload(
    job_id: str,
    asset_id: str,
    source_file: str,
    name: str,
    description: str,
    tags: list[str],
    is_private: bool,
) -> None:
    """Background-Task: Sketchfab-Upload ausführen und Job-Status aktualisieren."""

    svc = _get_sketchfab_service()
    if not svc:
        return

    async def update_job(
        status: str,
        result_url: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationJob).where(GenerationJob.id == UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = status
                job.updated_at = datetime.now(timezone.utc)
                if result_url is not None:
                    job.result_url = result_url
                if error_msg is not None:
                    job.error_msg = error_msg
                await session.commit()

    try:
        result: SketchfabUploadResult = await svc.upload_model(
            asset_id=asset_id,
            source_file=source_file,
            name=name,
            description=description,
            tags=tags,
            is_private=is_private,
        )
        now = datetime.now(timezone.utc).isoformat()
        asset_service.update_metadata_fields(
            asset_id,
            {
                "sketchfab_upload": {
                    "uid": result.uid,
                    "url": result.url,
                    "embed_url": result.embed_url,
                    "uploaded_at": now,
                    "is_private": is_private,
                }
            },
        )
        await update_job("done", result_url=result.url)
    except Exception as e:
        await update_job("failed", error_msg=str(e))


@router.get(
    "/assets/{asset_id}/sketchfab/status",
    response_model=SketchfabUploadStatusResponse,
)
async def get_sketchfab_upload_status(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Upload-Status für das letzte Sketchfab-Upload-Job dieses Assets."""
    meta = asset_service.get_asset(asset_id)
    if not meta:
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")

    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise_api_error(404, "Ungültige Asset-ID", code="INVALID_ASSET_ID")

    # Neuester sketchfab_upload Job für dieses Asset
    result = await session.execute(
        select(GenerationJob)
        .where(
            GenerationJob.job_type == "sketchfab_upload",
            GenerationJob.asset_id == asset_uuid,
        )
        .order_by(GenerationJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()

    if not job:
        # Prüfen ob bereits in metadata
        meta_path = asset_service.get_asset_dir(asset_id) / "metadata.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            sf = data.get("sketchfab_upload", {})
            if sf:
                return SketchfabUploadStatusResponse(
                    job_id="",
                    status="done",
                    sketchfab_uid=sf.get("uid"),
                    sketchfab_url=sf.get("url"),
                    embed_url=sf.get("embed_url"),
                )
        return SketchfabUploadStatusResponse(
            job_id="", status="none", error_msg="Kein Upload-Job für dieses Asset"
        )

    sketchfab_uid = None
    sketchfab_url = job.result_url
    embed_url = None
    if job.status == "done" and job.result_url:
        # UID aus URL extrahieren
        parts = (job.result_url or "").rstrip("/").split("/")
        if parts:
            sketchfab_uid = parts[-1]
        meta_path = asset_service.get_asset_dir(asset_id) / "metadata.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            sf = data.get("sketchfab_upload", {})
            if sf:
                embed_url = sf.get("embed_url")

    return SketchfabUploadStatusResponse(
        job_id=str(job.id),
        status=job.status,
        sketchfab_uid=sketchfab_uid,
        sketchfab_url=sketchfab_url,
        embed_url=embed_url,
        error_msg=job.error_msg,
    )


@router.post(
    "/assets/sketchfab/import",
    response_model=SketchfabImportResponse,
)
async def import_from_sketchfab(body: SketchfabImportRequest):
    """Importiert Modell von Sketchfab als neues Asset."""
    svc = _get_sketchfab_service()
    if not svc:
        raise_api_error(
            503,
            "Sketchfab nicht konfiguriert. SKETCHFAB_API_TOKEN in .env setzen.",
            code="SERVICE_UNAVAILABLE",
        )

    try:
        asset_id = await svc.download_model(
            sketchfab_url_or_uid=body.url,
            target_name=body.name,
        )
        return SketchfabImportResponse(asset_id=asset_id)
    except ValueError as e:
        raise_api_error(422, "Ungültige Anfrage", detail=str(e), code="VALIDATION_ERROR", chain=e)
    except RuntimeError as e:
        if "nicht zum Download freigegeben" in str(e):
            raise_api_error(403, "Zugriff verweigert", detail=str(e), code="FORBIDDEN", chain=e)
        raise_api_error(502, "Sketchfab-Fehler", detail=str(e), code="UPSTREAM_ERROR", chain=e)


@router.get("/sketchfab/me/models", response_model=SketchfabMeModelsResponse)
async def list_my_sketchfab_models():
    """Listet eigene Sketchfab-Modelle mit Thumbnails."""
    svc = _get_sketchfab_service()
    if not svc:
        raise_api_error(
            503,
            "Sketchfab nicht konfiguriert. SKETCHFAB_API_TOKEN in .env setzen.",
            code="SERVICE_UNAVAILABLE",
        )

    try:
        models = await svc.list_my_models()
        return SketchfabMeModelsResponse(
            models=[
                SketchfabModelItem(
                    uid=m["uid"],
                    name=m["name"],
                    url=m["url"],
                    thumbnail_url=m["thumbnail_url"],
                    vertex_count=m["vertex_count"],
                    face_count=m["face_count"],
                    is_downloadable=m["is_downloadable"],
                    created_at=m["created_at"],
                )
                for m in models
            ]
        )
    except RuntimeError as e:
        raise_api_error(502, "Sketchfab-Fehler", detail=str(e), code="UPSTREAM_ERROR", chain=e)
