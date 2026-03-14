"""Pydantic-Schemas für Asset-API."""

from datetime import datetime

from pydantic import BaseModel, Field


class AssetStepInfo(BaseModel):
    """Kompakte Step-Info für Listen-Response."""

    job_id: str
    provider_key: str
    file: str
    generated_at: str | None = None


class AssetListItem(BaseModel):
    """Ein Asset in der Liste GET /assets."""

    asset_id: str
    created_at: datetime | str
    updated_at: datetime | str
    steps: dict[str, AssetStepInfo] = Field(default_factory=dict)
    thumbnail_url: str | None = None  # Erste Bild-URL falls vorhanden


class AssetDetailResponse(BaseModel):
    """Vollständige metadata.json für GET /assets/{asset_id}."""

    asset_id: str
    created_at: str
    updated_at: str
    steps: dict[str, dict] = Field(default_factory=dict)
    processing: list[dict] = Field(
        default_factory=list,
        description="Mesh-Processing-Einträge (simplify, repair)",
    )


class CreateAssetResponse(BaseModel):
    """Response für POST /assets."""

    asset_id: str


class UploadAssetResponse(BaseModel):
    """Response für POST /assets/upload/image und /upload/mesh."""

    asset_id: str
    file: str  # Dateiname des erstellten Steps (z.B. image_original.png, mesh.glb)
