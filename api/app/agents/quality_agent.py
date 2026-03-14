"""Qualitätsbewertung von AI-generierten 3D-Meshes für Charakter-Pipeline."""

from pydantic_ai import Agent

from app.agents.base import get_model
from app.agents.models import QualityAssessment

_QUALITY_AGENT: Agent[None, QualityAssessment] | None = None


def get_quality_agent() -> Agent[None, QualityAssessment]:
    """Lazy-Initialisierung des Quality-Agenten (erfordert ANTHROPIC_API_KEY)."""
    global _QUALITY_AGENT
    if _QUALITY_AGENT is None:
        _QUALITY_AGENT = Agent(
            model=get_model(),
            output_type=QualityAssessment,
            system_prompt="""
Du bewertest die Qualität von AI-generierten 3D-Meshes für eine Charakter-Pipeline.
Du erhältst ein Bild des Meshes (oder Vorschau-Bild) und optionale Mesh-Kennzahlen.

Bewerte nach diesen Kriterien:
- Vollständigkeit: Sind alle Körperteile vorhanden? Keine fehlenden Gliedmaßen?
- Artefakte: Boden, Sockel, schwebende Geometry, doppelte Faces?
- Topologie: Ist die Mesh-Qualität für Rigging geeignet?
- Watertight: Ist der Mesh geschlossen (relevant für 3D-Druck)?
- Detail-Level: Angemessene Polygon-Dichte?

Erkannte Probleme klassifiziere als:
- type: "floor_artifact" | "missing_limb" | "bad_topology" | "not_watertight" |
        "floating_geometry" | "low_detail" | "high_poly" | "pose_issue"
- severity: "low" | "medium" | "high"

rigging_suitable: true nur wenn keine high-severity issues vorhanden.

Empfohlene Aktionen (recommended_actions) sollen konkrete nächste Schritte sein,
z.B. clip_floor bei Boden-Artefakt, repair_mesh bei Löchern, simplify bei zu vielen
Polygonen. action muss einer sein von: clip_floor, repair_mesh, remove_components,
simplify, rig, animate, export_stl, export_obj, sketchfab_upload.
""",
        )
    return _QUALITY_AGENT
