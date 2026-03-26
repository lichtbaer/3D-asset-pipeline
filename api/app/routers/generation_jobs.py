"""Job listing and stats sub-router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import GenerationJob
from app.schemas.generation import (
    JobListItem,
    JobListResponse,
    JobStatsResponse,
    JobTypeStats,
)

router = APIRouter()


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
