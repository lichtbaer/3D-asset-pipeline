"""ARIA-Router: Subagent-Tasks, Integrate, Task-Status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.aria.tools import delegate_to_subagent, get_task_status, integrate_task_result
from app.database import get_session
from app.schemas.subagent import (
    DelegateToSubagentRequest,
    DelegateToSubagentResponse,
    IntegrateTaskRequest,
    IntegrateTaskResponse,
    SubagentTaskResponse,
)
from app.services.subagent_service import get_tasks_for_panel

router = APIRouter(prefix="/api/v1", tags=["aria"])


@router.post(
    "/companies/{company_id}/aria/delegate",
    response_model=DelegateToSubagentResponse,
)
async def delegate(
    company_id: str,
    body: DelegateToSubagentRequest,
) -> DelegateToSubagentResponse:
    """Erstellt einen neuen Subagent-Task (delegate_to_subagent)."""
    result = await delegate_to_subagent(
        type=body.type,
        subproject_id=body.subproject_id,
        input_payload=body.input_payload,
        company_id=company_id,
    )
    return DelegateToSubagentResponse(**result)


@router.get(
    "/companies/{company_id}/aria/tasks",
    response_model=dict,
)
async def list_tasks(
    company_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Listet aktive Tasks + letzte 5 completed/failed für Frontend-Panel."""
    active, recent = await get_tasks_for_panel(session, company_id=company_id)

    def _serialize(t) -> dict:
        return {
            "id": str(t.id),
            "type": t.type,
            "status": t.status,
            "subproject_id": t.subproject_id,
            "input_payload": t.input_payload,
            "output_payload": t.output_payload,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "last_heartbeat_at": (
                t.last_heartbeat_at.isoformat() if t.last_heartbeat_at else None
            ),
            "integrated_at": (
                t.integrated_at.isoformat() if t.integrated_at else None
            ),
        }

    return {
        "active": [_serialize(t) for t in active],
        "recent": [_serialize(t) for t in recent],
    }


@router.get(
    "/companies/{company_id}/aria/tasks/{task_id}",
    response_model=SubagentTaskResponse,
)
async def get_task_status_route(
    company_id: str,
    task_id: str,
) -> SubagentTaskResponse:
    """Gibt Status eines Tasks zurück."""
    task = await get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task nicht gefunden")
    return task


@router.post(
    "/companies/{company_id}/aria/integrate-task",
    response_model=IntegrateTaskResponse,
)
async def integrate_task(
    company_id: str,
    body: IntegrateTaskRequest,
    session: AsyncSession = Depends(get_session),
) -> IntegrateTaskResponse:
    """
    Triggert Integration des Tasks.
    Ruft integrate_task_result auf (ARIA-gesteuert).
    """
    result = await integrate_task_result(body.task_id, session=session)
    return IntegrateTaskResponse(
        summary=result["summary"],
        integrated=result["integrated"],
    )
