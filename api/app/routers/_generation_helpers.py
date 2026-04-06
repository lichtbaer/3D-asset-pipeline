"""Shared helpers for generation sub-routers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.models import GenerationJob
from app.services.job_service import extract_asset_id_from_url, get_job_service

_job_svc = get_job_service()

_extract_asset_id_from_url = extract_asset_id_from_url


async def resolve_asset_id(
    asset_id_str: str | None,
    source_job_id: UUID | None,
    source_url: str | None,
    session: AsyncSession,
) -> UUID | None:
    """
    Löst asset_id in drei Schritten auf:
    1. Direkt übergebene asset_id (nach UUID parsen)
    2. asset_id des Quell-Jobs (source_job_id)
    3. asset_id aus URL extrahieren (source_url)
    """
    asset_id: UUID | None = None

    if asset_id_str:
        try:
            asset_id = UUID(asset_id_str)
        except ValueError:
            raise_api_error(422, f"Ungültige asset_id: {asset_id_str}", code="VALIDATION_ERROR")

    if asset_id is None and source_job_id:
        result = await session.execute(
            select(GenerationJob).where(GenerationJob.id == source_job_id)
        )
        src_job = result.scalar_one_or_none()
        if src_job and src_job.asset_id:
            asset_id = src_job.asset_id

    if asset_id is None and source_url:
        aid = extract_asset_id_from_url(source_url)
        if aid:
            asset_id = aid

    return asset_id


async def _update_job(
    job_id: str,
    status: str,
    result_path: str | None,
    error_msg: str | None = None,
    *,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Delegiert an JobService für Image-Jobs."""
    if status == "processing":
        await _job_svc.start(job_id)
    elif status == "done":
        await _job_svc.complete(job_id, result_url=result_path)
    elif status == "failed":
        await _job_svc.fail(
            job_id,
            error_msg or "Unknown error",
            error_type=error_type,
            error_detail=error_detail,
        )


async def _update_glb_job(
    job_id: str,
    status: str,
    result_path: str | None,
    error_msg: str | None = None,
    *,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Delegiert an JobService für Mesh/Rigging/Animation-Jobs."""
    if status == "processing":
        await _job_svc.start(job_id)
    elif status == "done":
        await _job_svc.complete(job_id, glb_file_path=result_path)
    elif status == "failed":
        await _job_svc.fail(
            job_id,
            error_msg or "Unknown error",
            error_type=error_type,
            error_detail=error_detail,
        )


async def _update_mesh_job_bgremoval(
    job_id: str, bgremoval_provider_key: str, bgremoval_result_url: str
) -> None:
    """Delegiert an JobService für BgRemoval-Felder bei Mesh-Jobs."""
    await _job_svc.update_bgremoval_fields(
        job_id, bgremoval_provider_key, bgremoval_result_url
    )


async def _update_bgremoval_job(
    job_id: str,
    status: str,
    result_path: str | None,
    error_msg: str | None = None,
    *,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Delegiert an JobService für BgRemoval-Jobs."""
    if status == "processing":
        await _job_svc.start(job_id)
    elif status == "done":
        await _job_svc.complete(
            job_id,
            result_url=result_path,
            bgremoval_result_url=result_path,
        )
    elif status == "failed":
        await _job_svc.fail(
            job_id,
            error_msg or "Unknown error",
            error_type=error_type,
            error_detail=error_detail,
        )
