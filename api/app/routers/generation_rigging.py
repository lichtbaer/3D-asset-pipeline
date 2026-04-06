"""Rigging sub-router."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.core.rate_limit import limiter
from app.database import get_session
from app.models import GenerationJob
from app.providers.rigging import (
    get_rigging_provider,
    list_rigging_providers,
)
from app.routers._generation_helpers import (
    _update_glb_job,
    resolve_asset_id,
)
from app.schemas.generation import (
    RiggingGenerateRequest,
    RiggingGenerateResponse,
    RiggingJobStatusResponse,
    RiggingProviderInfo,
    RiggingProvidersResponse,
)
from app.services.rigging_generation import run_rigging

router = APIRouter()


@router.get("/rigging/providers", response_model=RiggingProvidersResponse)
async def list_rigging_providers_endpoint():
    """Listet alle verfügbaren Rigging-Provider."""
    providers = list_rigging_providers()
    return RiggingProvidersResponse(
        providers=[
            RiggingProviderInfo(
                key=p.key,
                display_name=p.display_name,
            )
            for p in providers
        ]
    )


@router.post("/rigging", response_model=RiggingGenerateResponse, status_code=202)
@limiter.limit("10/minute")
async def create_rigging(
    request: Request,
    body: RiggingGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    try:
        get_rigging_provider(body.provider_key)
    except ValueError:
        raise_api_error(422, f"Unbekannter provider_key: {body.provider_key}", code="UNKNOWN_PROVIDER")

    asset_id = await resolve_asset_id(
        body.asset_id, None, body.source_glb_url, session
    )

    job = GenerationJob(
        job_type="rigging",
        status="pending",
        prompt="[rigging]",
        provider_key=body.provider_key,
        source_image_url=body.source_glb_url,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_rigging,
        str(job.id),
        body.source_glb_url,
        body.provider_key,
        str(asset_id) if asset_id else None,
        _update_glb_job,
    )

    return RiggingGenerateResponse(job_id=job.id, status="pending")


@router.post("/rigging/retry/{job_id}", response_model=RiggingGenerateResponse, status_code=202)
async def retry_rigging_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Erstellt neuen Job mit gleichen Parametern wie fehlgeschlagener Job."""
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "rigging",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")
    if job.status != "failed":
        raise_api_error(400, "Nur fehlgeschlagene Jobs können erneut versucht werden", code="INVALID_STATE")

    source_glb_url = job.source_image_url or ""
    if not source_glb_url:
        raise_api_error(400, "Quell-GLB-URL fehlt für Retry", code="MISSING_SOURCE")

    provider_key = job.provider_key or "unirig"

    new_job = GenerationJob(
        job_type="rigging",
        status="pending",
        prompt="[rigging]",
        provider_key=provider_key,
        source_image_url=source_glb_url,
        asset_id=job.asset_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    background_tasks.add_task(
        run_rigging,
        str(new_job.id),
        source_glb_url,
        provider_key,
        str(job.asset_id) if job.asset_id else None,
        _update_glb_job,
    )

    return RiggingGenerateResponse(job_id=new_job.id, status="pending")


@router.get("/rigging/{job_id}", response_model=RiggingJobStatusResponse)
async def get_rigging_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "rigging",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")

    glb_url = None
    if job.status == "done" and job.glb_file_path:
        glb_url = f"/static/meshes/{job.id}_rigged.glb"

    return RiggingJobStatusResponse(
        job_id=job.id,
        status=job.status,
        glb_url=glb_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        source_glb_url=job.source_image_url or "",
        provider_key=job.provider_key or "unirig",
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        failed_at=job.updated_at if job.status == "failed" else None,
    )
