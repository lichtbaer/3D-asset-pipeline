"""Schemas für die Pipeline-Automatisierung (One-Click Full Pipeline)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    """Anfrage für einen automatisierten Pipeline-Durchlauf."""

    prompt: str = Field(..., min_length=1, max_length=2000, description="Text-Prompt für die Bildgenerierung")
    image_provider_key: str = Field(default="picsart-default", description="Provider für Bildgenerierung")
    image_params: dict = Field(default_factory=dict, description="Parameter für Bildgenerierung")

    mesh_provider_key: str = Field(default="hunyuan3d-2", description="Provider für Mesh-Generierung")
    mesh_params: dict = Field(default_factory=dict, description="Parameter für Mesh-Generierung")

    enable_bgremoval: bool = Field(default=True, description="Background-Removal vor Mesh-Generierung")
    bgremoval_provider_key: str = Field(default="rembg-local", description="Provider für Background-Removal")

    enable_rigging: bool = Field(default=False, description="Rigging nach Mesh-Generierung")
    rigging_provider_key: str = Field(default="unirig", description="Provider für Rigging")

    enable_animation: bool = Field(default=False, description="Animation nach Rigging")
    animation_provider_key: str = Field(default="hy-motion", description="Provider für Animation")
    motion_prompt: str = Field(default="walk forward", description="Motion-Prompt für Animation")


class PipelineStepStatus(BaseModel):
    """Status eines einzelnen Pipeline-Schritts."""

    step: str
    job_id: UUID | None = None
    status: str  # pending | processing | done | failed | skipped
    result_url: str | None = None
    error: str | None = None


class PipelineRunStatus(BaseModel):
    """Status eines laufenden Pipeline-Durchlaufs."""

    pipeline_run_id: str
    status: str  # running | done | failed
    asset_id: UUID | None = None
    steps: list[PipelineStepStatus]
    created_at: datetime
    updated_at: datetime | None = None
    error: str | None = None


class PipelineRunResponse(BaseModel):
    """Antwort auf POST /generate/pipeline/run."""

    pipeline_run_id: str
    status: str
    asset_id: UUID | None = None
    steps: list[PipelineStepStatus]
    created_at: datetime
