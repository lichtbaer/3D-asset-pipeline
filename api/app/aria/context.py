"""ARIA Kontext-Builder – Subagenten-Tasks in System-Prompt injizieren."""

from datetime import datetime, timezone

from app.database import async_session_factory
from app.services.subagent_service import get_active_tasks_summary


def _format_age(dt: datetime) -> str:
    """Formatiert Alter seit dt (z.B. '2m', '1h')."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


async def build_subagent_context(company_id: str = "default") -> str:
    """Baut Kontext-String mit aktiven Subagenten-Tasks für ARIA-System-Prompt."""
    async with async_session_factory() as session:
        tasks = await get_active_tasks_summary(session, company_id=company_id)

    if not tasks:
        return ""

    status_icons = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✓",
        "failed": "✗",
        "timeout": "⚠",
    }
    lines = ["[Aktive Subagenten-Tasks]"]
    for task in tasks:
        icon = status_icons.get(task.status, "?")
        age = _format_age(task.created_at)
        heartbeat = ""
        if task.last_heartbeat_at:
            heartbeat = f", Heartbeat {_format_age(task.last_heartbeat_at)}"
        integrated = ""
        if task.integrated_at:
            integrated = " (integriert)"
        elif task.status == "completed":
            integrated = " (nicht integriert)"
        lines.append(
            f"- {str(task.id)[:8]}: {task.type} — {task.status} {icon} "
            f"({age}{heartbeat}){integrated}"
        )
    return "\n".join(lines)
