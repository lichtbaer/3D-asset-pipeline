"""Job listing, stats and SSE-Streaming sub-router."""

import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_session
from app.models import GenerationJob
from app.models.enums import JobStatus
from app.schemas.generation import (
    JobListItem,
    JobListResponse,
    JobStatsResponse,
    JobTypeStats,
)

router = APIRouter()


class PromptHistoryItem(BaseModel):
    prompt: str
    last_used_at: str
    use_count: int


class PromptHistoryResponse(BaseModel):
    items: list[PromptHistoryItem]


@router.get("/prompts/history", response_model=PromptHistoryResponse)
async def get_prompt_history(
    limit: int = Query(default=30, ge=1, le=100, description="Maximale Anzahl Einträge"),
    session: AsyncSession = Depends(get_session),
):
    """Distinct Prompts aus Image-Jobs, sortiert nach letzter Verwendung."""
    result = await session.execute(
        select(
            GenerationJob.prompt,
            func.max(GenerationJob.created_at).label("last_used_at"),
            func.count(GenerationJob.id).label("use_count"),
        )
        .where(GenerationJob.job_type == "image")
        .where(GenerationJob.prompt.isnot(None))
        .where(GenerationJob.prompt != "")
        .group_by(GenerationJob.prompt)
        .order_by(func.max(GenerationJob.created_at).desc())
        .limit(limit)
    )
    rows = result.all()
    return PromptHistoryResponse(
        items=[
            PromptHistoryItem(
                prompt=row.prompt,
                last_used_at=row.last_used_at.isoformat(),
                use_count=row.use_count,
            )
            for row in rows
        ]
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    job_type: str | None = Query(default=None, description="Filtert nach Job-Typ: image, bgremoval, mesh, rigging, animation"),
    status: str | None = Query(default=None, description="Filtert nach Status: pending, processing, done, failed"),
    asset_id: UUID | None = Query(default=None, description="Filtert nach Asset-ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximale Anzahl Ergebnisse"),
    offset: int = Query(default=0, ge=0, description="Anzahl übersprungener Ergebnisse"),
    session: AsyncSession = Depends(get_session),
):
    """Paginierte Liste aller Jobs mit optionalen Filtern."""
    query = select(GenerationJob)
    count_query = select(func.count()).select_from(GenerationJob)

    if job_type is not None:
        query = query.where(GenerationJob.job_type == job_type)
        count_query = count_query.where(GenerationJob.job_type == job_type)
    if status is not None:
        query = query.where(GenerationJob.status == status)
        count_query = count_query.where(GenerationJob.status == status)
    if asset_id is not None:
        query = query.where(GenerationJob.asset_id == asset_id)
        count_query = count_query.where(GenerationJob.asset_id == asset_id)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(GenerationJob.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[
            JobListItem(
                job_id=j.id,
                job_type=j.job_type,
                status=j.status,
                provider_key=j.provider_key or "",
                prompt=j.prompt if j.job_type == "image" else None,
                asset_id=j.asset_id,
                created_at=j.created_at,
                updated_at=j.updated_at,
                error_type=j.error_type,
            )
            for j in jobs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(session: AsyncSession = Depends(get_session)):
    """Statistiken über alle Jobs, gruppiert nach Typ und Status."""
    result = await session.execute(
        select(
            GenerationJob.job_type,
            GenerationJob.status,
            func.count().label("cnt"),
        ).group_by(GenerationJob.job_type, GenerationJob.status)
    )
    rows = result.all()

    # Aggregation nach job_type
    agg: dict[str, dict[str, int]] = {}
    for job_type, status, cnt in rows:
        if job_type not in agg:
            agg[job_type] = {"total": 0, "pending": 0, "processing": 0, "done": 0, "failed": 0}
        agg[job_type]["total"] += cnt
        if status in agg[job_type]:
            agg[job_type][status] += cnt

    by_type = [
        JobTypeStats(
            job_type=jt,
            total=stats["total"],
            pending=stats["pending"],
            processing=stats["processing"],
            done=stats["done"],
            failed=stats["failed"],
        )
        for jt, stats in sorted(agg.items())
    ]

    return JobStatsResponse(
        total_jobs=sum(s.total for s in by_type),
        by_type=by_type,
    )


# ---------------------------------------------------------------------------
# SSE-Streaming
# ---------------------------------------------------------------------------

_SSE_POLL_INTERVAL = 2.0   # Sekunden zwischen DB-Abfragen
_SSE_TIMEOUT = 600.0        # Maximale Stream-Dauer in Sekunden (10 Minuten)


async def _stream_job_events(job_id: UUID) -> AsyncGenerator[str, None]:
    """Generiert SSE-Events für einen Job bis zum Abschluss oder Timeout."""
    elapsed = 0.0
    last_status: str | None = None

    while elapsed < _SSE_TIMEOUT:
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationJob).where(GenerationJob.id == job_id)
            )
            job = result.scalar_one_or_none()

        if job is None:
            payload = json.dumps({"error": "Job nicht gefunden", "job_id": str(job_id)})
            yield f"event: error\ndata: {payload}\n\n"
            return

        status = job.status

        # Immer senden wenn sich der Status geändert hat (oder beim ersten Mal)
        if status != last_status:
            data: dict = {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": status,
                "result_url": job.result_url,
                "glb_file_path": job.glb_file_path,
                "asset_id": str(job.asset_id) if job.asset_id else None,
                "error_type": job.error_type,
                "error_detail": job.error_detail,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
            yield f"data: {json.dumps(data)}\n\n"
            last_status = status

        if status in (JobStatus.DONE, JobStatus.FAILED):
            yield "event: done\ndata: {}\n\n"
            return

        await asyncio.sleep(_SSE_POLL_INTERVAL)
        elapsed += _SSE_POLL_INTERVAL

    # Timeout erreicht
    yield "event: timeout\ndata: {\"reason\": \"stream_timeout\"}\n\n"


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: UUID):
    """
    Server-Sent Events (SSE) Stream für Job-Status-Updates.

    Sendet bei jedem Status-Wechsel ein SSE-Event bis der Job DONE oder FAILED ist.
    Timeout nach 10 Minuten.
    """
    return StreamingResponse(
        _stream_job_events(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
