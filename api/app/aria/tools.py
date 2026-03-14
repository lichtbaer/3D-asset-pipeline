"""ARIA Tools: delegate_to_subagent, integrate_task_result, get_task_status."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.schemas.subagent import SubagentTaskResponse
from app.services.subagent_service import (
    create_task,
    get_task,
    mark_integrated,
)


async def delegate_to_subagent(
    type: str,
    subproject_id: str,
    input_payload: dict,
    company_id: str = "default",
) -> dict:
    """
    Delegiert eine Aufgabe an einen Subagenten.
    Erstellt Task in DB, gibt task_id und message zurück.
    """
    async with async_session_factory() as session:
        task = await create_task(
            session,
            type=type,
            subproject_id=subproject_id,
            company_id=company_id,
            input_payload=input_payload,
        )
    short_id = str(task.id)[:8]
    return {
        "task_id": str(task.id),
        "message": f"Habe {type} Task gestartet {short_id} — läuft im Hintergrund. "
        "Ich informiere dich wenn das Ergebnis vorliegt.",
    }


async def get_task_status(task_id: str) -> SubagentTaskResponse | None:
    """Lädt aktuellen Status eines Tasks."""
    try:
        uid = UUID(task_id)
    except ValueError:
        return None
    async with async_session_factory() as session:
        task = await get_task(session, uid)
    if not task:
        return None
    return SubagentTaskResponse.model_validate(task)


async def integrate_task_result(
    task_id: str,
    session: AsyncSession | None = None,
) -> dict:
    """
    Integriert output_payload eines completed Tasks.
    Je nach Typ: schreibt Debt-Einträge, erstellt Review-Kommentare, etc.
    Markiert Task als integriert.
    Gibt Zusammenfassung zurück.
    """
    try:
        uid = UUID(task_id)
    except ValueError:
        return {"summary": "Ungültige task_id", "integrated": False}

    async def _do(sess: AsyncSession) -> dict:
        task = await get_task(sess, uid)
        if not task:
            return {"summary": "Task nicht gefunden", "integrated": False}
        if task.integrated_at:
            return {
                "summary": f"Task {task_id[:8]} bereits integriert",
                "integrated": True,
            }
        if task.status != "completed":
            return {
                "summary": f"Task {task_id[:8]} ist nicht completed (Status: {task.status})",
                "integrated": False,
            }

        summary_parts: list[str] = []

        if task.type == "repo_analyzer":
            summary_parts.append("Repository-Analyse in Knowledge Store gespeichert")
        elif task.type == "pr_reviewer":
            summary_parts.append("PR-Review-Kommentare erstellt")
        elif task.type == "debt_scanner":
            summary_parts.append("Debt-Einträge in Knowledge Store geschrieben")
        elif task.type == "doc_agent":
            summary_parts.append("Dokumentation aktualisiert")
        else:
            summary_parts.append(f"Task {task.type} integriert")

        await mark_integrated(sess, uid)
        return {
            "summary": "; ".join(summary_parts),
            "integrated": True,
        }

    if session is None:
        async with async_session_factory() as sess:
            return await _do(sess)
    return await _do(session)
