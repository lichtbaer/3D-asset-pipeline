from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model_key: str = "picsart-default"
    width: int = 1024
    height: int = 1024
    negative_prompt: str | None = None


class ImageGenerateResponse(BaseModel):
    job_id: UUID
    status: str


class ImageJobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    result_url: str | None = None
    error_msg: str | None = None
    model_key: str
    created_at: datetime


class ModelsResponse(BaseModel):
    models: list[str]


class MeshGenerateRequest(BaseModel):
    source_image_url: str = Field(..., min_length=1)
    source_job_id: UUID | None = None
    provider_key: str = "hunyuan3d-2"
    params: dict = Field(default_factory=dict)
    # Legacy: steps wird für hunyuan3d-2 in params übernommen
    steps: int | None = Field(default=None, ge=1, le=50)


class MeshProviderInfo(BaseModel):
    key: str
    display_name: str
    default_params: dict
    param_schema: dict


class MeshProvidersResponse(BaseModel):
    providers: list[MeshProviderInfo]


class MeshGenerateResponse(BaseModel):
    job_id: UUID
    status: str


class MeshJobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    glb_url: str | None = None
    error_msg: str | None = None
    source_image_url: str
    provider_key: str  # NULL in DB → "hunyuan3d-2" (Rückwärtskompatibilität)
    created_at: datetime
