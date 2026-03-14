"""Pydantic-Schemas für Bild-Nachbearbeitung (Crop, Resize, Center, Pad-Square)."""

from pydantic import BaseModel, Field


class CropRequest(BaseModel):
    """Request für POST /assets/{asset_id}/image/crop."""

    source_file: str = Field(..., description="z.B. image_bgremoved.png")
    x: int = Field(..., ge=0, description="X-Koordinate links oben")
    y: int = Field(..., ge=0, description="Y-Koordinate links oben")
    width: int = Field(..., gt=0, description="Crop-Breite in Pixel")
    height: int = Field(..., gt=0, description="Crop-Höhe in Pixel")


class ResizeRequest(BaseModel):
    """Request für POST /assets/{asset_id}/image/resize."""

    source_file: str = Field(..., description="z.B. image_bgremoved.png")
    width: int = Field(..., gt=0, description="Ziel-Breite")
    height: int = Field(..., gt=0, description="Ziel-Höhe")
    maintain_aspect: bool = Field(
        default=True,
        description="Seitenverhältnis beibehalten (mit Padding)",
    )


class CenterRequest(BaseModel):
    """Request für POST /assets/{asset_id}/image/center."""

    source_file: str = Field(..., description="z.B. image_bgremoved.png")
    padding: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Padding als Anteil der Subjekt-Größe (0.1 = 10%)",
    )


class PadSquareRequest(BaseModel):
    """Request für POST /assets/{asset_id}/image/pad-square."""

    source_file: str = Field(..., description="z.B. image_bgremoved.png")
    background: str = Field(
        default="white",
        description="white | black | transparent",
    )


class ImageProcessingResponse(BaseModel):
    """Response für alle Bild-Processing-Endpunkte."""

    output_file: str
    width: int
    height: int
    file_size_bytes: int
