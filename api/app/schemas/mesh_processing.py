"""Pydantic-Schemas für Mesh-Processing-API."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RepairOperation(str, Enum):
    """Repair-Operationen für Mesh-Bearbeitung."""

    REMOVE_DUPLICATES = "remove_duplicates"
    FIX_NORMALS = "fix_normals"
    FILL_HOLES = "fill_holes"
    REMOVE_DEGENERATE = "remove_degenerate"


class MeshAnalysis(BaseModel):
    """Analyse-Ergebnis eines Meshes."""

    vertex_count: int
    face_count: int
    is_watertight: bool
    is_manifold: bool
    has_duplicate_vertices: bool
    bounding_box: dict[str, float] = Field(
        description="min_x, max_x, min_y, max_y, min_z, max_z"
    )
    file_size_bytes: int


class SimplifyRequest(BaseModel):
    """Request für POST /assets/{asset_id}/process/simplify."""

    source_file: str = Field(..., description="z.B. mesh.glb")
    target_faces: int = Field(..., ge=1, description="Ziel-Anzahl Faces")


class RepairRequest(BaseModel):
    """Request für POST /assets/{asset_id}/process/repair."""

    source_file: str = Field(..., description="z.B. mesh.glb")
    operations: list[RepairOperation] = Field(
        ..., min_length=1, description="Liste der Repair-Operationen"
    )


class ClipFloorRequest(BaseModel):
    """Request für POST /assets/{asset_id}/process/clip-floor."""

    source_file: str = Field(..., description="z.B. mesh.glb")
    y_threshold: float | None = Field(
        default=None,
        description="Y-Schwellwert; null = Auto-Detect (untere 5%)",
    )


class RemoveComponentsRequest(BaseModel):
    """Request für POST /assets/{asset_id}/process/remove-components."""

    source_file: str = Field(..., description="z.B. mesh.glb")
    min_component_ratio: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Komponenten unter X% der Hauptmesh-Größe werden entfernt",
    )


class ProcessingResult(BaseModel):
    """Response für simplify/repair."""

    output_file: str
    processing: dict = Field(
        description="Eintrag für metadata.json processing-Array"
    )


class TextureBakeRequest(BaseModel):
    """Request für POST /assets/{asset_id}/texture/bake."""

    source_mesh: str = Field(..., description="High-Poly mit Texturen, z.B. mesh.glb")
    target_mesh: str = Field(
        ...,
        description="Low-Poly ohne Texturen, z.B. mesh_simplified_10000.glb",
    )
    resolution: int = Field(
        default=1024,
        ge=512,
        le=2048,
        description="Textur-Auflösung: 512, 1024, 2048",
    )
    bake_types: list[str] = Field(
        default=["diffuse", "roughness", "metallic"],
        description="Bake-Typen: diffuse, roughness, metallic",
    )

    @field_validator("bake_types")
    @classmethod
    def validate_bake_types(cls, v: list[str]) -> list[str]:
        valid = {"diffuse", "roughness", "metallic"}
        filtered = [t for t in v if t in valid]
        return filtered if filtered else ["diffuse", "roughness", "metallic"]


class TextureBakeStartResponse(BaseModel):
    """Response für POST /assets/{asset_id}/texture/bake (Job gestartet)."""

    job_id: str
    status: str = "pending"


class TextureBakeStatusResponse(BaseModel):
    """Response für GET /assets/{asset_id}/texture/bake/status/{job_id}."""

    job_id: str
    status: str  # pending | processing | done | failed
    output_file: str | None = None
    duration_seconds: float | None = None
    error_msg: str | None = None
