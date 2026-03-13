"""Pydantic-Schemas für Mesh-Processing-API."""

from enum import Enum

from pydantic import BaseModel, Field


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


class ProcessingResult(BaseModel):
    """Response für simplify/repair."""

    output_file: str
    processing: dict = Field(
        description="Eintrag für metadata.json processing-Array"
    )
