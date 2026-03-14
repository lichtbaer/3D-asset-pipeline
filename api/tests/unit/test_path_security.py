"""
Unit-Tests für path_security.py.
Path-Traversal-Schutz für Asset-Dateizugriffe.
"""

import uuid

import pytest
from fastapi import HTTPException

from app.core import path_security


def test_path_traversal_rejected(tmp_storage_paths):
    """Path-Traversal mit ../../etc/passwd wird abgelehnt."""
    asset_id = str(uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        path_security.safe_asset_path(asset_id, "../../etc/passwd")
    assert exc_info.value.status_code == 400
    assert "Invalid filename" in str(exc_info.value.detail)


def test_invalid_asset_id_rejected(tmp_storage_paths):
    """Ungültige asset_id (kein UUID) wird abgelehnt."""
    with pytest.raises(HTTPException) as exc_info:
        path_security.safe_asset_path("not-a-uuid", "mesh.glb")
    assert exc_info.value.status_code == 400
    assert "Invalid asset_id" in str(exc_info.value.detail)


def test_valid_filename_accepted(tmp_storage_paths):
    """Gültiger Dateiname wird akzeptiert."""
    asset_id = str(uuid.uuid4())
    path = path_security.safe_asset_path(asset_id, "mesh_simplified_10000.glb")
    assert path.name == "mesh_simplified_10000.glb"
    assert asset_id in str(path)


def test_absolute_path_traversal_rejected(tmp_storage_paths):
    """Absoluter Pfad-Versuch wird abgelehnt."""
    asset_id = str(uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        path_security.safe_asset_path(asset_id, "/etc/passwd")
    assert exc_info.value.status_code == 400
