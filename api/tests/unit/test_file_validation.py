"""
Unit-Tests für file_validation.py.
Magic-Bytes, Extension, Größe, Path-Traversal.
"""

import pytest
from fastapi import HTTPException

from app.core import file_validation


class MockUploadFile:
    """Mock für FastAPI UploadFile mit konfigurierbarem Inhalt."""

    def __init__(self, content: bytes, filename: str) -> None:
        self._content = content
        self.filename = filename

    async def read(self) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_valid_png_accepted():
    """Magic Bytes: PNG wird akzeptiert."""
    file = MockUploadFile(content=b"\x89PNG\r\n\x1a\n" + b"x" * 100, filename="test.png")
    result = await file_validation.validate_image_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_valid_jpeg_accepted():
    """Magic Bytes: JPEG wird akzeptiert."""
    file = MockUploadFile(content=b"\xff\xd8\xff" + b"x" * 100, filename="test.jpg")
    result = await file_validation.validate_image_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_jpeg_with_wrong_extension_rejected():
    """JPEG-Inhalt mit .txt Extension wird abgelehnt."""
    file = MockUploadFile(content=b"\xff\xd8\xff" + b"x" * 100, filename="test.txt")
    with pytest.raises(HTTPException) as exc_info:
        await file_validation.validate_image_upload(file)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_webp_accepted():
    """WebP wird akzeptiert (RIFF....WEBP)."""
    header = b"RIFF" + b"\x00" * 4 + b"WEBP"
    file = MockUploadFile(content=header + b"x" * 100, filename="test.webp")
    result = await file_validation.validate_image_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_invalid_extension_rejected():
    """Ungültige Extension wird abgelehnt."""
    file = MockUploadFile(content=b"\x89PNG\r\n\x1a\n", filename="test.bmp")
    with pytest.raises(HTTPException) as exc_info:
        await file_validation.validate_image_upload(file)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_file_too_large_rejected():
    """Bild > 20 MB wird abgelehnt."""
    file = MockUploadFile(
        content=b"\x89PNG\r\n\x1a\n" + b"x" * (21 * 1024 * 1024),
        filename="huge.png",
    )
    with pytest.raises(HTTPException) as exc_info:
        await file_validation.validate_image_upload(file)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_magic_bytes_mismatch_rejected():
    """PNG-Extension aber falscher Inhalt wird abgelehnt."""
    file = MockUploadFile(content=b"NOTPNGxxxxx", filename="fake.png")
    with pytest.raises(HTTPException) as exc_info:
        await file_validation.validate_image_upload(file)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_glb_magic_bytes_accepted():
    """GLB Magic Bytes werden akzeptiert."""
    file = MockUploadFile(content=b"glTF" + b"x" * 100, filename="mesh.glb")
    result = await file_validation.validate_mesh_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_gltf_json_accepted():
    """GLTF JSON (beginnt mit {) wird akzeptiert."""
    file = MockUploadFile(content=b'{"asset":{"version":"2.0"}}', filename="mesh.gltf")
    result = await file_validation.validate_mesh_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_obj_accepted():
    """OBJ-Format wird akzeptiert."""
    file = MockUploadFile(content=b"o cube\nv 0 0 0", filename="mesh.obj")
    result = await file_validation.validate_mesh_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_ply_accepted():
    """PLY-Format wird akzeptiert."""
    file = MockUploadFile(content=b"ply\nformat ascii 1.0", filename="mesh.ply")
    result = await file_validation.validate_mesh_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_stl_ascii_accepted():
    """STL ASCII wird akzeptiert."""
    file = MockUploadFile(content=b"solid cube\nfacet normal 0 0 0", filename="mesh.stl")
    result = await file_validation.validate_mesh_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_zip_accepted():
    """ZIP-Format wird akzeptiert."""
    file = MockUploadFile(content=b"PK\x03\x04" + b"x" * 100, filename="mesh.zip")
    result = await file_validation.validate_mesh_upload(file)
    assert result == file._content


@pytest.mark.asyncio
async def test_mesh_invalid_extension_rejected():
    """Ungültige Mesh-Extension wird abgelehnt."""
    file = MockUploadFile(content=b"glTF", filename="mesh.xyz")
    with pytest.raises(HTTPException) as exc_info:
        await file_validation.validate_mesh_upload(file)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_mesh_too_large_rejected():
    """Mesh > 100 MB wird abgelehnt."""
    file = MockUploadFile(
        content=b"glTF" + b"x" * (101 * 1024 * 1024),
        filename="huge.glb",
    )
    with pytest.raises(HTTPException) as exc_info:
        await file_validation.validate_mesh_upload(file)
    assert exc_info.value.status_code == 422
