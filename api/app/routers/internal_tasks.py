"""Interne Task-Queue-API für Subagenten (repo_analyzer etc.).

SUBAGENT-001: Bereitstellung der Task-Queue.
Endpoints werden von Subagenten-Containern aufgerufen (INTERNAL_API_KEY).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.schemas.subagent_task import RepoAnalysisOutput

router = APIRouter(prefix="/api/v1/internal/tasks", tags=["internal-tasks"])

# In-Memory Task-Queue (MVP). Später: DB-Persistenz.
_tasks: dict[str, dict[str, Any]] = {}
_pending_tasks: list[str] = []


def _verify_internal_key(x_internal_api_key: str | None) -> None:
    """Prüft INTERNAL_API_KEY gegen ENV."""
    import os

    expected = os.getenv("INTERNAL_API_KEY")
    if not expected or x_internal_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing INTERNAL_API_KEY")


@router.get("/next")
async def get_next_task(
    type: str,
    x_internal_api_key: str | None = Header(None, alias="X-Internal-Api-Key"),
):
    """Holt den nächsten Task für den angegebenen Typ (z.B. repo_analyzer)."""
    _verify_internal_key(x_internal_api_key)

    for task_id in list(_pending_tasks):
        t = _tasks.get(task_id)
        if t and t.get("type") == type and t.get("status") == "pending":
            t["status"] = "processing"
            return {
                "id": task_id,
                "type": type,
                "input_payload": t.get("input_payload", {}),
                "status": "processing",
            }
    return None


@router.post("/{task_id}/heartbeat")
async def heartbeat(
    task_id: str,
    x_internal_api_key: str | None = Header(None, alias="X-Internal-Api-Key"),
):
    """Heartbeat während der Verarbeitung."""
    _verify_internal_key(x_internal_api_key)
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    # Optional: last_heartbeat aktualisieren
    return {"ok": True}


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    result: RepoAnalysisOutput,
    x_internal_api_key: str | None = Header(None, alias="X-Internal-Api-Key"),
):
    """Markiert Task als abgeschlossen mit Ergebnis."""
    _verify_internal_key(x_internal_api_key)
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks[task_id]["status"] = "completed"
    _tasks[task_id]["result"] = result.model_dump()
    if task_id in _pending_tasks:
        _pending_tasks.remove(task_id)
    return {"ok": True}


class FailTaskBody(BaseModel):
    error: str


@router.post("/{task_id}/fail")
async def fail_task(
    task_id: str,
    body: FailTaskBody,
    x_internal_api_key: str | None = Header(None, alias="X-Internal-Api-Key"),
):
    """Markiert Task als fehlgeschlagen."""
    _verify_internal_key(x_internal_api_key)
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks[task_id]["status"] = "failed"
    _tasks[task_id]["error"] = body.error
    if task_id in _pending_tasks:
        _pending_tasks.remove(task_id)
    return {"ok": True}


# Enqueue-Endpoint für Tests / ARIA (später)
@router.post("/enqueue")
async def enqueue_task(
    type: str,
    input_payload: dict[str, Any],
    x_internal_api_key: str | None = Header(None, alias="X-Internal-Api-Key"),
):
    """Fügt einen neuen Task zur Queue hinzu (für Tests)."""
    _verify_internal_key(x_internal_api_key)
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "id": task_id,
        "type": type,
        "input_payload": input_payload,
        "status": "pending",
    }
    _pending_tasks.append(task_id)
    return {"id": task_id, "status": "pending"}
