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
    steps: int = Field(default=30, ge=1, le=50)


class MeshGenerateResponse(BaseModel):
    job_id: UUID
    status: str


class MeshJobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    glb_url: str | None = None
    error_msg: str | None = None
    source_image_url: str
    created_at: datetime
