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
