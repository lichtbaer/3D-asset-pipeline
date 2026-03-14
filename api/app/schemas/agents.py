"""Request-Schemas für Agent-Endpunkte (Details in PURZEL-037 bis 040)."""

from pydantic import BaseModel, Field

from app.agents.models import QualityAssessment


class PromptOptimizeRequest(BaseModel):
    """Request für Prompt-Optimierung (PURZEL-037)."""

    description: str = Field(..., min_length=1, description="Einfache Charakter-Beschreibung")
    style: str | None = Field(default=None, description="Stil: cartoon, realistic, pixel-art")
    intended_use: str = Field(
        default="rigging",
        description="Verwendung: rigging, mesh_only, 3d_print",
    )
    existing_prompt: str | None = Field(
        default=None,
        description="Optional: bestehender Prompt zur Verbesserung",
    )


class TagsSuggestRequest(BaseModel):
    """Request für Tag-Vorschläge (PURZEL-038)."""

    asset_id: str = Field(..., description="Asset-ID")
    prompt: str | None = Field(
        default=None,
        description="Generierungs-Prompt falls vorhanden",
    )
    original_filename: str | None = Field(
        default=None,
        description="Dateiname bei Uploads",
    )
    pipeline_steps: list[str] = Field(
        default_factory=list,
        description="Pipeline-Stand: image, mesh, rigging, animation",
    )
    include_image_analysis: bool = Field(
        default=False,
        description="Vision-Analyse des Vorschau-Bilds",
    )


class QualityAssessRequest(BaseModel):
    """Request für Qualitätsbewertung (PURZEL-039)."""

    asset_id: str = Field(..., description="Asset-ID")
    include_mesh_analysis: bool = Field(
        default=True,
        description="Analyse-Kennzahlen aus /process/analyze laden",
    )
    include_vision: bool = Field(
        default=True,
        description="Vorschau-Bild analysieren (image oder bgremoval)",
    )


class WorkflowRecommendRequest(BaseModel):
    """Request für Workflow-Empfehlung (PURZEL-040)."""

    asset_id: str = Field(..., description="Asset-ID")
    intention: str | None = Field(
        default=None,
        description="Nutzer-Intention: rig, print, animate, sketchfab",
    )
    quality_assessment: QualityAssessment | None = Field(
        default=None,
        description="Optional vorgeladene Qualitätsbewertung",
    )
