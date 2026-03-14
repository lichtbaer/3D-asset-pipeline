"""
Mesh-Processing-Service: optionale Simplification und Repair via Open3D/trimesh.
Alle Operationen sind nicht-destruktiv — das Original mesh.glb wird nie überschrieben.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import open3d as o3d
import trimesh

from app.schemas.mesh_processing import MeshAnalysis, RepairOperation
from app.services import asset_service

logger = logging.getLogger(__name__)


def _asset_mesh_path(asset_id: str, filename: str) -> Path:
    """Vollständiger Pfad zu Mesh-Datei im Asset-Ordner."""
    path = asset_service.get_file_path(asset_id, filename)
    if not path:
        raise FileNotFoundError(f"Datei {filename} nicht in Asset {asset_id}")
    return path


def _to_dict(box: o3d.geometry.AxisAlignedBoundingBox) -> dict[str, float]:
    """Bounding-Box zu Dict."""
    min_b = box.get_min_bound()
    max_b = box.get_max_bound()
    return {
        "min_x": float(min_b[0]),
        "max_x": float(max_b[0]),
        "min_y": float(min_b[1]),
        "max_y": float(max_b[1]),
        "min_z": float(min_b[2]),
        "max_z": float(max_b[2]),
    }


def analyze(asset_id: str, source_file: str) -> MeshAnalysis:
    """
    Analysiert Mesh, gibt Kennzahlen zurück. Erzeugt keine neue Datei.
    """
    source_path = _asset_mesh_path(asset_id, source_file)
    mesh = o3d.io.read_triangle_mesh(str(source_path))

    vertices = mesh.vertices
    triangles = mesh.triangles
    vertex_count = len(vertices)
    face_count = len(triangles)

    # Duplikate: vergleiche Vertex-Anzahl vor/nach remove_duplicated_vertices
    mesh_check = o3d.io.read_triangle_mesh(str(source_path))
    mesh_check.remove_duplicated_vertices()
    has_duplicates = len(mesh_check.vertices) < vertex_count

    # Watertight/Manifold: Open3D hat is_watertight, is_self_intersecting
    is_watertight = mesh.is_watertight()
    # Manifold: prüfen ob alle Kanten von genau 2 Faces geteilt werden
    is_manifold = mesh.is_edge_manifold()

    bbox = mesh.get_axis_aligned_bounding_box()
    file_size_bytes = source_path.stat().st_size

    return MeshAnalysis(
        vertex_count=vertex_count,
        face_count=face_count,
        is_watertight=is_watertight,
        is_manifold=is_manifold,
        has_duplicate_vertices=has_duplicates,
        bounding_box=_to_dict(bbox),
        file_size_bytes=file_size_bytes,
    )


def simplify(
    asset_id: str, source_file: str, target_faces: int
) -> tuple[str, dict[str, Any]]:
    """
    Vereinfacht Mesh auf target_faces Dreiecke.
    Speichert mesh_simplified_{target_faces}.glb, gibt Filename zurück.
    """
    source_path = _asset_mesh_path(asset_id, source_file)
    mesh = o3d.io.read_triangle_mesh(str(source_path))

    current_faces = len(mesh.triangles)
    effective_target = min(target_faces, current_faces)

    simplified = mesh.simplify_quadric_decimation(
        target_number_of_triangles=effective_target
    )
    output_filename = f"mesh_simplified_{target_faces}.glb"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    o3d.io.write_triangle_mesh(str(output_path), simplified)

    processed_at = datetime.now(timezone.utc).isoformat()

    entry = {
        "operation": "simplify",
        "params": {"target_faces": target_faces},
        "source_file": source_file,
        "output_file": output_filename,
        "processed_at": processed_at,
    }
    asset_service.append_processing_entry(asset_id, entry)
    logger.info(
        "Asset %s: simplify %s -> %s (%d faces)",
        asset_id,
        source_file,
        output_filename,
        target_faces,
    )
    return output_filename, entry


def repair(
    asset_id: str, source_file: str, operations: list[RepairOperation]
) -> tuple[str, dict[str, Any]]:
    """
    Repariert Mesh mit ausgewählten Operationen.
    Speichert mesh_repaired.glb, gibt Filename zurück.
    """
    source_path = _asset_mesh_path(asset_id, source_file)
    mesh = o3d.io.read_triangle_mesh(str(source_path))

    op_set = set(operations)

    if RepairOperation.REMOVE_DUPLICATES in op_set:
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()

    if RepairOperation.REMOVE_DEGENERATE in op_set:
        mesh.remove_degenerate_triangles()

    if RepairOperation.FIX_NORMALS in op_set:
        mesh.compute_vertex_normals()

    # fill_holes via trimesh (Open3D hat kein zuverlässiges fill_holes)
    if RepairOperation.FILL_HOLES in op_set:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            o3d.io.write_triangle_mesh(tmp_path, mesh)
            tmesh = trimesh.load(tmp_path, file_type="glb", force="mesh")
            if isinstance(tmesh, trimesh.Scene):
                dumped = tmesh.dump(concatenate=True)
                tmesh = dumped[0] if isinstance(dumped, list) else dumped
            trimesh.repair.fill_holes(tmesh)
            tmesh.export(tmp_path)
            mesh = o3d.io.read_triangle_mesh(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    output_filename = "mesh_repaired.glb"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    o3d.io.write_triangle_mesh(str(output_path), mesh)

    processed_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "operation": "repair",
        "params": {
            "operations": [op.value for op in operations],
        },
        "source_file": source_file,
        "output_file": output_filename,
        "processed_at": processed_at,
    }
    asset_service.append_processing_entry(asset_id, entry)
    logger.info(
        "Asset %s: repair %s -> %s (ops: %s)",
        asset_id,
        source_file,
        output_filename,
        [op.value for op in operations],
    )
    return output_filename, entry


def clip_floor(
    asset_id: str,
    source_file: str,
    y_threshold: float | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Schneidet alles unterhalb eines Y-Schwellwerts ab.
    y_threshold=None → Auto-Detect: untere 5% der Bounding Box.
    Speichert mesh_clipped.glb.
    """
    source_path = _asset_mesh_path(asset_id, source_file)
    mesh = o3d.io.read_triangle_mesh(str(source_path))

    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    vertex_count_before = len(vertices)
    face_count_before = len(triangles)

    if y_threshold is None:
        y_min = float(vertices[:, 1].min())
        y_max = float(vertices[:, 1].max())
        y_threshold = y_min + (y_max - y_min) * 0.05

    v0_y = vertices[triangles[:, 0], 1]
    v1_y = vertices[triangles[:, 1], 1]
    v2_y = vertices[triangles[:, 2], 1]
    all_above = (v0_y >= y_threshold) & (v1_y >= y_threshold) & (v2_y >= y_threshold)
    triangles_to_remove = ~all_above

    mesh.remove_triangles_by_mask(triangles_to_remove)
    mesh.remove_unreferenced_vertices()

    vertex_count_after = len(np.asarray(mesh.vertices))
    face_count_after = len(np.asarray(mesh.triangles))

    output_filename = "mesh_clipped.glb"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    o3d.io.write_triangle_mesh(str(output_path), mesh)

    processed_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "operation": "clip_floor",
        "params": {"y_threshold": y_threshold},
        "source_file": source_file,
        "output_file": output_filename,
        "processed_at": processed_at,
    }
    asset_service.append_processing_entry(asset_id, entry)
    logger.info(
        "Asset %s: clip_floor %s -> %s (y=%.4f, removed %d verts, %d faces)",
        asset_id,
        source_file,
        output_filename,
        y_threshold,
        vertex_count_before - vertex_count_after,
        face_count_before - face_count_after,
    )
    return output_filename, {
        "output_file": output_filename,
        "y_threshold_used": y_threshold,
        "vertices_removed": vertex_count_before - vertex_count_after,
        "faces_removed": face_count_before - face_count_after,
    }


def remove_small_components(
    asset_id: str,
    source_file: str,
    min_component_ratio: float = 0.05,
) -> tuple[str, dict[str, Any]]:
    """
    Entfernt kleine, nicht verbundene Komponenten.
    Komponenten kleiner als min_component_ratio * Hauptmesh werden entfernt.
    Speichert mesh_cleaned.glb.
    """
    source_path = _asset_mesh_path(asset_id, source_file)
    mesh = o3d.io.read_triangle_mesh(str(source_path))

    triangle_clusters, cluster_n_triangles, _ = mesh.cluster_connected_triangles()
    triangle_clusters = np.asarray(triangle_clusters)
    cluster_n_triangles = np.asarray(cluster_n_triangles)

    max_cluster = int(cluster_n_triangles.max())
    threshold = max_cluster * min_component_ratio
    components_found = len(cluster_n_triangles)

    triangles_to_remove = cluster_n_triangles[triangle_clusters] < threshold
    triangles_removed = int(triangles_to_remove.sum())
    components_removed = int((cluster_n_triangles < threshold).sum())

    mesh.remove_triangles_by_mask(triangles_to_remove)
    mesh.remove_unreferenced_vertices()

    output_filename = "mesh_cleaned.glb"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    o3d.io.write_triangle_mesh(str(output_path), mesh)

    processed_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "operation": "remove_components",
        "params": {"min_component_ratio": min_component_ratio},
        "source_file": source_file,
        "output_file": output_filename,
        "processed_at": processed_at,
    }
    asset_service.append_processing_entry(asset_id, entry)
    logger.info(
        "Asset %s: remove_components %s -> %s (removed %d components, %d triangles)",
        asset_id,
        source_file,
        output_filename,
        components_removed,
        triangles_removed,
    )
    return output_filename, {
        "output_file": output_filename,
        "components_found": components_found,
        "components_removed": components_removed,
        "triangles_removed": triangles_removed,
    }
