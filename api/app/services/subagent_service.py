"""Service für Subagent-Task-Operationen."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SubagentTask


async def create_task(
    session: AsyncSession,
    *,
    type: str,
    subproject_id: str,
    company_id: str,
    input_payload: dict,
) -> SubagentTask:
    """Erstellt einen neuen Subagent-Task."""
    task = SubagentTask(
        type=type,
        status="pending",
        subproject_id=subproject_id,
        company_id=company_id,
        input_payload=input_payload,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(session: AsyncSession, task_id: UUID) -> SubagentTask | None:
    """Lädt einen Task nach ID."""
    result = await session.execute(
        select(SubagentTask).where(SubagentTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def get_active_tasks_summary(
    session: AsyncSession,
    company_id: str = "default",
) -> list[SubagentTask]:
    """Lädt aktive Tasks: pending, running, completed (nicht integriert)."""
    result = await session.execute(
        select(SubagentTask)
        .where(SubagentTask.company_id == company_id)
        .where(
            (SubagentTask.status.in_(["pending", "running"]))
            | (
                (SubagentTask.status == "completed")
                & (SubagentTask.integrated_at.is_(None))
            )
        )
        .order_by(SubagentTask.created_at.desc())
    )
    return list(result.scalars().all())


async def get_tasks_for_panel(
    session: AsyncSession,
    company_id: str = "default",
) -> tuple[list[SubagentTask], list[SubagentTask]]:
    """Lädt Tasks für Frontend-Panel: aktive + letzte 5 completed/failed."""
    # Aktive (pending + running)
    active_result = await session.execute(
        select(SubagentTask)
        .where(SubagentTask.company_id == company_id)
        .where(SubagentTask.status.in_(["pending", "running"]))
        .order_by(SubagentTask.created_at.desc())
    )
    active = list(active_result.scalars().all())

    # Letzte 5 completed/failed
    recent_result = await session.execute(
        select(SubagentTask)
        .where(SubagentTask.company_id == company_id)
        .where(SubagentTask.status.in_(["completed", "failed", "timeout"]))
        .order_by(SubagentTask.created_at.desc())
        .limit(5)
    )
    recent = list(recent_result.scalars().all())

    return active, recent


async def mark_integrated(
    session: AsyncSession,
    task_id: UUID,
) -> SubagentTask | None:
    """Markiert Task als integriert."""
    task = await get_task(session, task_id)
    if not task:
        return None
    task.integrated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(task)
    return task
