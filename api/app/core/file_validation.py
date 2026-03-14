"""File-Upload-Validierung: Magic-Bytes, Extension, Größe."""

from fastapi import HTTPException, UploadFile

# Erlaubte Formate
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_MESH_TYPES = {
    "model/gltf-binary",
    "model/gltf+json",
    "application/octet-stream",
    "text/plain",
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MESH_EXTENSIONS = {".glb", ".gltf", ".obj", ".ply", ".stl", ".zip"}

MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_MESH_SIZE = 100 * 1024 * 1024  # 100 MB

# Magic bytes (Anfang der Datei)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
WEBP_SIGNATURE = b"RIFF"  # WebP: RIFF....WEBP
GLB_SIGNATURE = b"glTF"  # GLB: 4 Bytes "glTF" + 4 Bytes Version
GLTF_JSON_START = b"{"  # GLTF JSON beginnt mit {
OBJ_START = b"o "  # OBJ: typischerweise "o " oder "v "
PLY_START = b"ply"  # PLY: "ply\n"
STL_ASCII_START = b"solid "  # STL ASCII
STL_BINARY_START = b"\x00" * 5  # STL Binary: 80 bytes header, dann 4 bytes face count
ZIP_SIGNATURE = b"PK\x03\x04"  # ZIP


def _read_header(contents: bytes, size: int = 12) -> bytes:
    """Liest die ersten Bytes der Datei."""
    return contents[:size]


def _validate_image_magic_bytes(contents: bytes) -> bytes:
    """Prüft Magic-Bytes für Bildformate. Gibt den erkannten Typ zurück oder None."""
    header = _read_header(contents, 12)
    if header.startswith(PNG_SIGNATURE):
        return b"png"
    if header.startswith(JPEG_SIGNATURE):
        return b"jpeg"
    if len(header) >= 12 and header[:4] == WEBP_SIGNATURE and header[8:12] == b"WEBP":
        return b"webp"
    return b""


def _validate_mesh_magic_bytes(contents: bytes, ext: str) -> bool:
    """Prüft Magic-Bytes für Mesh-Formate. Extension hilft bei Mehrdeutigkeit."""
    header = _read_header(contents, 84)
    ext_lower = ext.lower()

    if ext_lower in (".glb",):
        return len(contents) >= 4 and contents[:4] == GLB_SIGNATURE
    if ext_lower in (".gltf",):
        return len(contents) >= 1 and contents[:1] == GLTF_JSON_START
    if ext_lower in (".obj",):
        return (
            header.startswith(b"o ")
            or header.startswith(b"v ")
            or header.startswith(b"# ")
            or header.startswith(b"g ")
        )
    if ext_lower in (".ply",):
        return header.startswith(PLY_START)
    if ext_lower in (".stl",):
        return header.startswith(STL_ASCII_START) or len(contents) >= 84
    if ext_lower in (".zip",):
        return header.startswith(ZIP_SIGNATURE)
    return False


async def validate_image_upload(file: UploadFile) -> bytes:
    """
    Validiert Bild-Upload: Extension, Magic-Bytes, Größe.
    Raises HTTPException(422) bei Fehler.
    Gibt den gelesenen Dateiinhalt zurück (für weitere Verarbeitung).
    """
    ext = "." + (file.filename or "").split(".")[-1].lower() if file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiges Format. Erlaubt: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"Datei zu groß. Maximum: {MAX_IMAGE_SIZE // (1024*1024)} MB",
        )
    detected = _validate_image_magic_bytes(content)
    if not detected:
        raise HTTPException(
            status_code=422,
            detail="Dateiinhalt entspricht keinem erlaubten Bildformat (PNG, JPEG, WebP)",
        )
    return content


async def validate_mesh_upload(file: UploadFile) -> bytes:
    """
    Validiert Mesh-Upload: Extension, Magic-Bytes, Größe.
    Raises HTTPException(422) bei Fehler.
    Gibt den gelesenen Dateiinhalt zurück.
    """
    ext = "." + (file.filename or "").split(".")[-1].lower() if file.filename else ""
    if ext not in ALLOWED_MESH_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiges Format. Erlaubt: {', '.join(ALLOWED_MESH_EXTENSIONS)}",
        )
    content = await file.read()
    if len(content) > MAX_MESH_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"Datei zu groß. Maximum: {MAX_MESH_SIZE // (1024*1024)} MB",
        )
    if not _validate_mesh_magic_bytes(content, ext):
        raise HTTPException(
            status_code=422,
            detail="Dateiinhalt entspricht keinem erlaubten Mesh-Format (GLB, GLTF, OBJ, PLY, STL, ZIP)",
        )
    return content
