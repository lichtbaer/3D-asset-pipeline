"""ARIA – Architect & Orchestrator für Subagenten-Delegation."""

from app.aria.context import build_subagent_context
from app.aria.prompts import ARIA_SYSTEM_PROMPT
from app.aria.tools import (
    delegate_to_subagent,
    get_task_status,
    integrate_task_result,
)

__all__ = [
    "build_subagent_context",
    "ARIA_SYSTEM_PROMPT",
    "delegate_to_subagent",
    "get_task_status",
    "integrate_task_result",
]
