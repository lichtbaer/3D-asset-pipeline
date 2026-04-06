"""Background removal sub-router."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.core.rate_limit import limiter
from app.database import get_session
from app.models import GenerationJob
from app.routers._generation_helpers import (
    _update_bgremoval_job,
    resolve_asset_id,
)
from app.schemas.generation import (
    BgRemovalGenerateRequest,
    BgRemovalGenerateResponse,
    BgRemovalJobStatusResponse,
    BgRemovalProviderInfo,
    BgRemovalProvidersResponse,
)
from app.services.bgremoval import run_bgremoval
from app.services.bgremoval_providers import (
    get_provider as get_bgremoval_provider,
)
from app.services.bgremoval_providers import (
    list_providers as list_bgremoval_providers,
)

router = APIRouter()


@router.get("/bgremoval/providers", response_model=BgRemovalProvidersResponse)
async def list_bgremoval_providers_endpoint():
    """Listet alle verfügbaren Background-Removal-Provider."""
    providers = list_bgremoval_providers()
    return BgRemovalProvidersResponse(
        providers=[
            BgRemovalProviderInfo(
                key=p.provider_key,
                display_name=p.display_name,
                default_params=p.default_params(),
                param_schema=p.param_schema(),
            )
            for p in providers
        ]
    )


@router.post("/bgremoval", response_model=BgRemovalGenerateResponse, status_code=202)
@limiter.limit("10/minute")
async def create_bgremoval(
    request: Request,
    body: BgRemovalGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    try:
        get_bgremoval_provider(body.provider_key)
    except ValueError:
        raise_api_error(422, f"Unbekannter provider_key: {body.provider_key}", code="UNKNOWN_PROVIDER")

    asset_id = await resolve_asset_id(
        body.asset_id, body.source_job_id, body.source_image_url, session
    )

    job = GenerationJob(
        job_type="bgremoval",
        status="pending",
        prompt="[bgremoval]",
        provider_key=body.provider_key,
        source_image_url=body.source_image_url,
        source_job_id=body.source_job_id,
        bgremoval_provider_key=body.provider_key,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_bgremoval,
        str(job.id),
        body.source_image_url,
        body.provider_key,
        _update_bgremoval_job,
    )

    return BgRemovalGenerateResponse(job_id=job.id, status="pending")


@router.get("/bgremoval/{job_id}", response_model=BgRemovalJobStatusResponse)
async def get_bgremoval_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "bgremoval",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")

    provider_key = job.bgremoval_provider_key or job.provider_key or ""
    return BgRemovalJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.bgremoval_result_url or job.result_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        source_image_url=job.source_image_url or "",
        provider_key=provider_key,
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        failed_at=job.updated_at if job.status == "failed" else None,
    )


@router.post("/bgremoval/retry/{job_id}", response_model=BgRemovalGenerateResponse, status_code=202)
async def retry_bgremoval_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Erstellt neuen Job mit gleichen Parametern wie fehlgeschlagener Job."""
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "bgremoval",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")
    if job.status != "failed":
        raise_api_error(400, "Nur fehlgeschlagene Jobs können erneut versucht werden", code="INVALID_STATE")

    source_image_url = job.source_image_url or ""
    if not source_image_url:
        raise_api_error(400, "Quellbild-URL fehlt für Retry", code="MISSING_SOURCE")

    provider_key = job.bgremoval_provider_key or job.provider_key or ""

    new_job = GenerationJob(
        job_type="bgremoval",
        status="pending",
        prompt="[bgremoval]",
        provider_key=provider_key,
        source_image_url=source_image_url,
        source_job_id=job.source_job_id,
        bgremoval_provider_key=provider_key,
        asset_id=job.asset_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    background_tasks.add_task(
        run_bgremoval,
        str(new_job.id),
        source_image_url,
        provider_key,
        _update_bgremoval_job,
    )

    return BgRemovalGenerateResponse(job_id=new_job.id, status="pending")
