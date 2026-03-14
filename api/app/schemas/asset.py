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
    exports: list[dict] = Field(
        default_factory=list,
        description="Export-Einträge (STL, OBJ, PLY, GLTF)",
    )


class ExportRequest(BaseModel):
    """Request für POST /assets/{asset_id}/export."""

    source_file: str = Field(..., description="z.B. mesh.glb")
    format: str = Field(..., description="stl | obj | ply | gltf")


class ExportResponse(BaseModel):
    """Response für POST /assets/{asset_id}/export."""

    output_file: str
    format: str
    file_size_bytes: int
    download_url: str


class ExportListItem(BaseModel):
    """Ein Export in GET /assets/{asset_id}/exports."""

    filename: str
    format: str
    source_file: str
    exported_at: str
    file_size_bytes: int
    download_url: str


class ExportsListResponse(BaseModel):
    """Response für GET /assets/{asset_id}/exports."""

    exports: list[ExportListItem]


class CreateAssetResponse(BaseModel):
    """Response für POST /assets."""

    asset_id: str


class UploadAssetResponse(BaseModel):
    """Response für POST /assets/upload/image und /upload/mesh."""

    asset_id: str
    file: str  # Dateiname des erstellten Steps (z.B. image_original.png, mesh.glb)
