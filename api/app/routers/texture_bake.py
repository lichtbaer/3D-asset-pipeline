"""Texture-Baking-Routen: Start und Status-Abfrage von Bake-Jobs."""

import asyncio
import logging
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.core.path_security import safe_asset_path
from app.database import async_session_factory, get_session
from app.exceptions import (
    BlenderNotAvailableError,
    TextureBakingError,
    TextureBakingTimeoutError,
)
from app.models import TextureBakeJob
from app.schemas.mesh_processing import (
    TextureBakeRequest,
    TextureBakeStartResponse,
    TextureBakeStatusResponse,
)
from app.services import asset_service
from app.services.texture_baking_service import run_bake_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


async def _run_texture_bake_task(
    job_id: UUID,
    asset_id: str,
    source_mesh: str,
    target_mesh: str,
    resolution: int,
    bake_types: list[str],
) -> None:
    """Background-Task: Texture-Baking ausführen; Status in texture_bake_job."""
    from datetime import datetime, timezone

    async with async_session_factory() as session:
        await session.execute(
            update(TextureBakeJob)
            .where(TextureBakeJob.id == job_id)
            .values(status="processing")
        )
        await session.commit()

    started = time.monotonic()

    async def _set_job_failed(msg: str) -> None:
        async with async_session_factory() as s:
            await s.execute(
                update(TextureBakeJob)
                .where(TextureBakeJob.id == job_id)
                .values(
                    status="failed",
                    output_file=None,
                    duration_seconds=round(time.monotonic() - started, 1),
                    error_msg=msg,
                )
            )
            await s.commit()

    try:
        output_file = await asyncio.to_thread(
            run_bake_sync,
            asset_id=asset_id,
            source_mesh=source_mesh,
            target_mesh=target_mesh,
            resolution=resolution,
            bake_types=bake_types,
        )
        duration = time.monotonic() - started
        async with async_session_factory() as session:
            await session.execute(
                update(TextureBakeJob)
                .where(TextureBakeJob.id == job_id)
                .values(
                    status="done",
                    output_file=output_file,
                    duration_seconds=round(duration, 1),
                    error_msg=None,
                )
            )
            await session.commit()
        entry = {
            "source_mesh": source_mesh,
            "target_mesh": target_mesh,
            "output_file": output_file,
            "resolution": resolution,
            "bake_types": bake_types,
            "baked_at": datetime.now(timezone.utc).isoformat(),
        }
        asset_service.append_texture_baking_entry(asset_id, entry)
    except (BlenderNotAvailableError, TextureBakingError, TextureBakingTimeoutError) as e:
        await _set_job_failed(str(e))
    except (ValueError, OSError, RuntimeError) as e:
        await _set_job_failed(str(e))


@router.post(
    "/{asset_id}/texture/bake",
    response_model=TextureBakeStartResponse,
    status_code=202,
)
async def start_texture_bake(
    asset_id: str,
    body: TextureBakeRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Startet Texture-Baking-Job. Baking läuft asynchron (30–120s)."""
    if not asset_service.get_asset(asset_id):
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")
    safe_asset_path(asset_id, body.source_mesh)
    safe_asset_path(asset_id, body.target_mesh)
    source_path = asset_service.get_file_path(asset_id, body.source_mesh)
    target_path = asset_service.get_file_path(asset_id, body.target_mesh)
    if not source_path or not source_path.is_file():
        raise_api_error(
            404,
            f"Source-Mesh {body.source_mesh} nicht gefunden",
            code="FILE_NOT_FOUND",
        )
    if not target_path or not target_path.is_file():
        raise_api_error(
            404,
            f"Target-Mesh {body.target_mesh} nicht gefunden",
            code="FILE_NOT_FOUND",
        )
    try:
        aid = UUID(asset_id)
    except ValueError:
        raise_api_error(400, "Ungültige asset_id", code="INVALID_PARAM")
    job_uuid = uuid.uuid4()
    session.add(
        TextureBakeJob(
            id=job_uuid,
            asset_id=aid,
            status="pending",
            source_mesh=body.source_mesh,
            target_mesh=body.target_mesh,
            resolution=body.resolution,
            bake_types=list(body.bake_types),
        )
    )
    await session.commit()
    background_tasks.add_task(
        _run_texture_bake_task,
        job_uuid,
        asset_id,
        body.source_mesh,
        body.target_mesh,
        body.resolution,
        body.bake_types,
    )
    return TextureBakeStartResponse(job_id=str(job_uuid), status="pending")


@router.get(
    "/{asset_id}/texture/bake/status/{job_id}",
    response_model=TextureBakeStatusResponse,
)
async def get_texture_bake_status(
    asset_id: str,
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Status eines Texture-Baking-Jobs abfragen."""
    if not asset_service.get_asset(asset_id):
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")
    try:
        jid = UUID(job_id)
        aid = UUID(asset_id)
    except ValueError:
        raise_api_error(400, "Ungültige UUID", code="INVALID_PARAM")
    result = await session.execute(
        select(TextureBakeJob).where(
            TextureBakeJob.id == jid,
            TextureBakeJob.asset_id == aid,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")
    return TextureBakeStatusResponse(
        job_id=str(job.id),
        status=job.status,
        output_file=job.output_file,
        duration_seconds=job.duration_seconds,
        error_msg=job.error_msg,
    )
