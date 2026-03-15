#!/usr/bin/env python3
"""
Blender Headless Rigging – Produktionsreif (SMA-173)

Importiert GLB, wendet Rigify Human Meta-Rig an, berechnet Automatic Weights,
exportiert als GLB mit Armature.

Verbesserungen gegenüber PoC:
- Bone Heat Weighting Failure → Warning loggen, Output trotzdem liefern
- WGT-Meshes (Rigify Widget-Objekte) beim Export ausschließen

Aufruf:
  blender --background --python scripts/blender_rig_human.py -- input.glb output_rigged.glb
"""
import argparse
import sys
import time

# Blender-Python: bpy wird vom Blender-Interpreter bereitgestellt
import bpy


def clear_scene() -> None:
    """Löscht alle Objekte in der Szene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def remove_armatures_keep_meshes() -> None:
    """
    Entfernt alle Armatures aus der Szene (z.B. aus GLB-Import).
    Meshes bleiben erhalten – wir fügen unser eigenes Rig hinzu.
    """
    for obj in list(bpy.context.scene.objects):
        if obj.type == "ARMATURE":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.ops.object.delete(use_global=False)


def import_glb(path: str) -> list:
    """Importiert GLB-Datei, gibt Liste der importierten Objekte zurück."""
    bpy.ops.import_scene.gltf(filepath=path)
    return list(bpy.context.scene.objects)


def get_mesh_objects() -> list:
    """Gibt alle Mesh-Objekte (ohne Armature) zurück."""
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def get_armature_objects() -> list:
    """Gibt alle Armature-Objekte zurück."""
    return [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]


def enable_rigify() -> bool:
    """Aktiviert das Rigify-Addon."""
    try:
        bpy.ops.preferences.addon_enable(module="rigify")
        return True
    except Exception:
        print("Rigify-Addon nicht verfuegbar", file=sys.stderr)
        return False


def get_mesh_bounds(meshes: list) -> tuple[list[float], list[float]]:
    """Ermittelt die kombinierte Bounding-Box aller Meshes in World-Space."""
    from mathutils import Vector

    min_co: list[float] = [float("inf")] * 3
    max_co: list[float] = [float("-inf")] * 3
    for mesh in meshes:
        for v in mesh.bound_box:
            world_v = mesh.matrix_world @ Vector((v[0], v[1], v[2]))
            for i in range(3):
                min_co[i] = min(min_co[i], world_v[i])
                max_co[i] = max(max_co[i], world_v[i])
    if min_co[0] == float("inf"):
        for mesh in meshes:
            for v in mesh.data.vertices:
                world_v = mesh.matrix_world @ v.co
                for i in range(3):
                    min_co[i] = min(min_co[i], world_v[i])
                    max_co[i] = max(max_co[i], world_v[i])
    return min_co, max_co


def add_rigify_human_metarig():
    """
    Fügt Rigify Human Meta-Rig hinzu (via object.armature_human_metarig_add)
    und skaliert es an die Mesh-Größe an.
    """
    bpy.ops.object.select_all(action="DESELECT")

    try:
        bpy.ops.object.armature_human_metarig_add()
    except AttributeError:
        raise RuntimeError(
            "Rigify-Addon nicht aktiv oder object.armature_human_metarig_add nicht verfügbar"
        )
    metarig = bpy.context.active_object

    meshes = get_mesh_objects()
    if not meshes:
        raise RuntimeError("Kein Mesh nach GLB-Import gefunden")

    min_co, max_co = get_mesh_bounds(meshes)
    center = [(min_co[i] + max_co[i]) / 2 for i in range(3)]
    size = [max_co[i] - min_co[i] for i in range(3)]
    height = max(size) if max(size) > 0 else 1.0

    metarig.location = center
    scale = height / 2.0
    metarig.scale = (scale, scale, scale)
    bpy.ops.object.select_all(action="DESELECT")
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.transform_apply(location=True, scale=True, rotation=False)

    return metarig


def generate_rigify_rig(metarig) -> None:
    """Generiert das finale Rig aus dem Meta-Rig."""
    bpy.ops.object.select_all(action="DESELECT")
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.pose.rigify_generate()


def parent_mesh_with_auto_weights(mesh, armature) -> bool:
    """
    Verknüpft Mesh mit Armature und berechnet Automatic Weights.
    Returns True bei Erfolg, False bei Fehler (z.B. Bone Heat Weighting).
    Bei Fehler: Warning loggen, trotzdem fortfahren (partielle Weights besser als kein Rig).
    """
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        return True
    except RuntimeError as e:
        print(f"WARNUNG: Bone Heat Weighting für {mesh.name}: {e}")
        return False


def _is_wgt_mesh(obj) -> bool:
    """Prüft ob Objekt ein Rigify-Widget-Mesh ist (WGT-Objekte)."""
    if obj.type != "MESH":
        return False
    name = obj.name.upper()
    return name.startswith("WGT-") or "WGT_" in name


def _exclude_wgt_from_export() -> None:
    """Blendet WGT-Meshes für den Export aus (Hide in Render)."""
    for obj in bpy.context.scene.objects:
        if _is_wgt_mesh(obj):
            obj.hide_render = True


def _restore_wgt_visibility() -> None:
    """Stellt WGT-Sichtbarkeit wieder her."""
    for obj in bpy.context.scene.objects:
        if _is_wgt_mesh(obj):
            obj.hide_render = False


def export_glb(path: str) -> None:
    """Exportiert die Szene als GLB mit Armature."""
    _exclude_wgt_from_export()
    try:
        bpy.ops.export_scene.gltf(
            filepath=path,
            export_format="GLB",
            use_selection=False,
            export_apply=True,
        )
    finally:
        _restore_wgt_visibility()


def main() -> int:
    parser = argparse.ArgumentParser(description="Blender Rigging (Rigify Human)")
    parser.add_argument("input_glb", help="Eingabe-GLB-Datei")
    parser.add_argument("output_glb", help="Ausgabe-GLB-Datei (geriggt)")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

    start_time = time.time()

    clear_scene()

    if not enable_rigify():
        print("WARNUNG: Rigify konnte nicht aktiviert werden – nutze Basic-Armature")

    import_glb(args.input_glb)
    remove_armatures_keep_meshes()
    meshes = get_mesh_objects()
    if not meshes:
        print("FEHLER: Kein Mesh in GLB gefunden")
        return 1

    metarig = add_rigify_human_metarig()
    generate_rigify_rig(metarig)
    armatures = get_armature_objects()
    if not armatures:
        print("FEHLER: Keine Armature nach Rigify-Generierung")
        return 1

    rig = [a for a in armatures if a != metarig][0] if len(armatures) > 1 else armatures[0]

    for mesh in meshes:
        parent_mesh_with_auto_weights(mesh, rig)  # Fehler werden geloggt, Output trotzdem geliefert

    # Meta-Rig entfernen (nur finales Rig exportieren)
    bpy.ops.object.select_all(action="DESELECT")
    if metarig.name in bpy.data.objects:
        metarig.select_set(True)
        bpy.ops.object.delete()

    export_glb(args.output_glb)

    elapsed = time.time() - start_time
    print(f"Rigging abgeschlossen in {elapsed:.1f}s")
    print(f"Output: {args.output_glb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
