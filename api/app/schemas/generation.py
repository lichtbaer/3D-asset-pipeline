from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """Neues Format: provider_key + params."""

    prompt: str = Field(..., min_length=1)
    provider_key: str = Field(default="picsart-default", alias="provider_key")
    params: dict = Field(
        default_factory=lambda: {"width": 1024, "height": 1024},
        alias="params",
    )

    # Rückwärtskompatibilität: model_key + Top-Level-Parameter
    model_key: str | None = Field(default=None, alias="model_key")
    width: int | None = Field(default=None, alias="width")
    height: int | None = Field(default=None, alias="height")
    negative_prompt: str | None = Field(default=None, alias="negative_prompt")

    model_config = {"populate_by_name": True}

    def resolve_provider_and_params(self) -> tuple[str, dict]:
        """
        Ermittelt provider_key und params.
        Mappt altes Format (model_key + Top-Level) auf neues Format.
        """
        if self.model_key is not None:
            # Altes Format: model_key → provider_key mappen
            key_map = {
                "picsart-default": "picsart-default",
                "flux-dev": "picsart-flux-dev",
                "flux-max": "picsart-flux-max",
                "dalle3": "picsart-dalle3",
                "ideogram-2a": "picsart-ideogram",
            }
            provider_key = key_map.get(self.model_key, self.model_key)
            params = {
                "width": self.width if self.width is not None else 1024,
                "height": self.height if self.height is not None else 1024,
                "negative_prompt": self.negative_prompt,
                "count": 1,
            }
            return provider_key, params
        # Neues Format
        params = dict(self.params) if self.params else {}
        if "width" not in params:
            params["width"] = 1024
        if "height" not in params:
            params["height"] = 1024
        if "count" not in params:
            params["count"] = 1
        return self.provider_key, params


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


class ImageProviderInfo(BaseModel):
    """Einzelner Provider für GET /generate/image/providers."""

    key: str
    display_name: str
    default_params: dict
    param_schema: dict


class ImageProvidersResponse(BaseModel):
    """Response für GET /generate/image/providers."""

    providers: list[ImageProviderInfo]


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
