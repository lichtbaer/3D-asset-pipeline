"""Pydantic-Schemas für Pipeline-Presets."""

from pydantic import BaseModel, Field


class PresetStep(BaseModel):
    """Ein Step in einem Preset."""

    step: str = Field(
        ...,
        description="Step-Typ: image, bgremoval, mesh, clip_floor, remove_components, repair, simplify, rigging, animation, export, sketchfab_upload",
    )
    provider: str | None = Field(
        default=None,
        description="Provider-Key (für image, bgremoval, mesh, rigging, animation)",
    )
    params: dict = Field(default_factory=dict, description="Step-spezifische Parameter")


class PresetCreate(BaseModel):
    """Request für POST /presets."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    steps: list[PresetStep] = Field(default_factory=list)


class PresetUpdate(BaseModel):
    """Request für PUT /presets/{preset_id}."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    steps: list[PresetStep] | None = None


class PresetResponse(BaseModel):
    """Response für GET /presets und GET /presets/{preset_id}."""

    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    steps: list[PresetStep]


class PresetApplyRequest(BaseModel):
    """Request für POST /presets/{preset_id}/apply."""

    asset_id: str
    start_from_step: int = Field(default=0, ge=0)
    dry_run: bool = Field(default=False)


class ExecutionPlanItem(BaseModel):
    """Ein Eintrag im Execution-Plan."""

    step_index: int
    step: str
    provider: str | None
    params: dict
    status: str = Field(
        ...,
        description="skipped | applicable",
    )
    reason: str | None = Field(
        default=None,
        description="Kurze Begründung (z.B. 'bereits vorhanden')",
    )


class PresetApplyResponse(BaseModel):
    """Response für POST /presets/{preset_id}/apply."""

    preset_id: str
    asset_id: str
    steps_total: int
    steps_applicable: int
    steps_skipped: int
    execution_plan: list[ExecutionPlanItem]
