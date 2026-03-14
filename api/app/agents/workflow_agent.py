"""Workflow-Empfehlung für den nächsten Schritt in der 3D-Asset-Pipeline."""

from pydantic_ai import Agent

from app.agents.base import get_model
from app.agents.models import WorkflowRecommendation

_WORKFLOW_AGENT: Agent[None, WorkflowRecommendation] | None = None


def get_workflow_agent() -> Agent[None, WorkflowRecommendation]:
    """Lazy-Initialisierung des Workflow-Agenten (erfordert ANTHROPIC_API_KEY)."""
    global _WORKFLOW_AGENT
    if _WORKFLOW_AGENT is None:
        _WORKFLOW_AGENT = Agent(
            model=get_model(),
            output_type=WorkflowRecommendation,
            system_prompt="""
Du empfiehlst den optimalen nächsten Schritt in einer 3D-Asset-Pipeline.
Verfügbare Schritte: clip_floor, repair_mesh, remove_components,
simplify, rig, animate, export_stl, export_obj, sketchfab_upload.

Basis für die Empfehlung: Mesh-Kennzahlen, vorhandene Pipeline-Steps,
Qualitätsbewertung, und optionale Nutzer-Intention (rig, print, animate, sketchfab).

next_step muss immer einer der definierten Schritte sein.
alternative_steps: Liste alternativer sinnvoller Schritte (ebenfalls nur gültige Schritte).
warnings: Hinweise z.B. "Mesh ist nicht watertight — für 3D-Druck vorher repair ausführen".
""",
        )
    return _WORKFLOW_AGENT
