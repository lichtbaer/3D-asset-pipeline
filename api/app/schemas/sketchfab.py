"""Pydantic-Schemas für Sketchfab-API."""

from pydantic import BaseModel, Field


class SketchfabUploadRequest(BaseModel):
    """Request für POST /assets/{asset_id}/sketchfab/upload."""

    name: str = Field(..., min_length=1, description="Modellname auf Sketchfab")
    description: str = Field(default="", description="Optionale Beschreibung")
    tags: list[str] = Field(default_factory=list, description="Tags, kommasepariert oder als Liste")
    is_private: bool = Field(default=False, description="Privat (True) oder öffentlich (False)")
    source_file: str = Field(default="mesh.glb", description="Welche GLB-Datei aus dem Asset-Ordner")


class SketchfabUploadResponse(BaseModel):
    """Response für POST /assets/{asset_id}/sketchfab/upload (202)."""

    job_id: str
    status: str = "pending"


class SketchfabUploadStatusResponse(BaseModel):
    """Response für GET /assets/{asset_id}/sketchfab/status."""

    job_id: str
    status: str
    sketchfab_uid: str | None = None
    sketchfab_url: str | None = None
    embed_url: str | None = None
    error_msg: str | None = None


class SketchfabImportRequest(BaseModel):
    """Request für POST /assets/sketchfab/import."""

    url: str = Field(..., description="Sketchfab-URL oder Model-UID")
    name: str | None = Field(default=None, description="Optionale Anzeige für das Asset")


class SketchfabImportResponse(BaseModel):
    """Response für POST /assets/sketchfab/import."""

    asset_id: str


class SketchfabModelItem(BaseModel):
    """Ein Modell aus GET /sketchfab/me/models."""

    uid: str
    name: str
    url: str
    thumbnail_url: str
    vertex_count: int
    face_count: int
    is_downloadable: bool
    created_at: str


class SketchfabMeModelsResponse(BaseModel):
    """Response für GET /sketchfab/me/models."""

    models: list[SketchfabModelItem]


class SketchfabStatusResponse(BaseModel):
    """Response für GET /sketchfab/status (Feature-Flag)."""

    enabled: bool
