"""
Mesh-Export-Service: STL, OBJ, PLY, GLTF für 3D-Druck und externe Tools.
Nutzt Open3D und trimesh — alle Formate nativ unterstützt.
"""

import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import open3d as o3d
import trimesh

from app.services import asset_service

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ["stl", "obj", "ply", "gltf"]


def _asset_mesh_path(asset_id: str, filename: str) -> Path:
    """Vollständiger Pfad zu Mesh-Datei im Asset-Ordner."""
    path = asset_service.get_file_path(asset_id, filename)
    if not path:
        raise FileNotFoundError(f"Datei {filename} nicht in Asset {asset_id}")
    return path


def _output_filename(source_file: str, fmt: str) -> str:
    """Erzeugt output_filename: mesh.glb → mesh.stl, mesh_simplified_10000.glb → mesh_simplified_10000.stl."""
    stem = Path(source_file).stem
    return f"{stem}.{fmt}"


def _export_stl(asset_id: str, source_path: Path, output_path: Path) -> int:
    """STL-Export via Open3D."""
    mesh = o3d.io.read_triangle_mesh(str(source_path))
    o3d.io.write_triangle_mesh(str(output_path), mesh)
    return output_path.stat().st_size


def _export_obj(asset_id: str, source_path: Path, output_path: Path) -> tuple[str, int]:
    """
    OBJ-Export via Open3D. Erzeugt .obj + .mtl.
    Gibt (output_file, file_size_bytes) zurück.
    output_file ist eine ZIP mit beiden Dateien für einfachen Download.
    """
    mesh = o3d.io.read_triangle_mesh(str(source_path))
    obj_path = output_path
    o3d.io.write_triangle_mesh(
        str(obj_path), mesh, write_triangle_uvs=True, write_vertex_normals=True
    )
    mtl_path = obj_path.with_suffix(".mtl")
    zip_path = output_path.parent / f"{output_path.stem}_obj.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(obj_path, obj_path.name)
        if mtl_path.exists() and mtl_path.stat().st_size > 0:
            zf.write(mtl_path, mtl_path.name)
    return str(zip_path.name), zip_path.stat().st_size


def _export_ply(asset_id: str, source_path: Path, output_path: Path) -> int:
    """PLY-Export via Open3D."""
    mesh = o3d.io.read_triangle_mesh(str(source_path))
    o3d.io.write_triangle_mesh(str(output_path), mesh)
    return output_path.stat().st_size


def _export_gltf(asset_id: str, source_path: Path, output_path: Path) -> tuple[str, int]:
    """
    GLTF-Export (entpackt) via trimesh. Erzeugt .gltf + .bin.
    Gibt (output_file, file_size_bytes) zurück.
    output_file ist die .gltf-Datei (Hauptdatei).
    """
    mesh_tm = trimesh.load(str(source_path), file_type="glb", force="mesh")
    if isinstance(mesh_tm, trimesh.Scene):
        dumped = mesh_tm.dump(concatenate=True)
        mesh_tm = dumped[0] if isinstance(dumped, list) else dumped
    gltf_path = output_path.with_suffix(".gltf")
    mesh_tm.export(str(gltf_path))
    total_size = sum(
        f.stat().st_size
        for f in output_path.parent.glob(f"{output_path.stem}*")
        if f.suffix in (".gltf", ".bin")
    )
    return str(gltf_path.name), total_size


def export(
    asset_id: str,
    source_file: str,
    target_format: str,
) -> dict:
    """
    Exportiert Mesh in Zielformat.
    Returns: {output_file, format, file_size_bytes, download_url}
    """
    fmt = target_format.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Format {target_format} nicht unterstützt. Erlaubt: {SUPPORTED_FORMATS}")

    source_path = _asset_mesh_path(asset_id, source_file)
    asset_dir = asset_service.get_asset_dir(asset_id)
    output_filename = _output_filename(source_file, fmt)
    output_path = asset_dir / output_filename

    if fmt == "stl":
        file_size = _export_stl(asset_id, source_path, output_path)
        result_output = output_filename
    elif fmt == "obj":
        result_output, file_size = _export_obj(asset_id, source_path, output_path)
    elif fmt == "ply":
        file_size = _export_ply(asset_id, source_path, output_path)
        result_output = output_filename
    elif fmt == "gltf":
        result_output, file_size = _export_gltf(asset_id, source_path, output_path)
    else:
        raise ValueError(f"Format {fmt} nicht implementiert")

    exported_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "format": fmt,
        "source_file": source_file,
        "output_file": result_output,
        "exported_at": exported_at,
        "file_size_bytes": file_size,
    }
    _append_export_entry(asset_id, entry)

    base_url = f"/assets/{asset_id}/files"
    download_url = f"{base_url}/{result_output}"

    logger.info(
        "Asset %s: Export %s -> %s (%s, %d bytes)",
        asset_id,
        source_file,
        result_output,
        fmt,
        file_size,
    )

    return {
        "output_file": result_output,
        "format": fmt,
        "file_size_bytes": file_size,
        "download_url": download_url,
    }


def _append_export_entry(asset_id: str, entry: dict) -> None:
    """Fügt Export-Eintrag zu metadata.json exports-Array hinzu."""
    meta_path = asset_service.get_asset_dir(asset_id) / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "exports" not in meta:
        meta["exports"] = []
    meta["exports"].append(entry)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def list_exports(asset_id: str) -> list[dict]:
    """Listet alle in metadata.json dokumentierten Exports."""
    meta = asset_service.get_asset(asset_id)
    if not meta:
        return []
    exports = meta.exports
    result = []
    base_url = f"/assets/{asset_id}/files"
    for e in exports:
        result.append(
            {
                "filename": e.get("output_file", ""),
                "format": e.get("format", ""),
                "source_file": e.get("source_file", ""),
                "exported_at": e.get("exported_at", ""),
                "file_size_bytes": e.get("file_size_bytes", 0),
                "download_url": f"{base_url}/{e.get('output_file', '')}",
            }
        )
    return result
