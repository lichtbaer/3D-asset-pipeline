#!/usr/bin/env python3
"""
Blender Headless Rigging PoC – SMA-172

Importiert GLB, wendet Rigify Human Meta-Rig an, berechnet Automatic Weights,
exportiert als GLB mit Armature.

Aufruf:
  blender --background --python scripts/blender_rig_test.py -- input.glb output_rigged.glb
"""
import argparse
import sys
import time

# Blender-Python: bpy wird vom Blender-Interpreter bereitgestellt
import bpy


def clear_scene():
    """Löscht alle Objekte in der Szene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def remove_armatures_keep_meshes():
    """
    Entfernt alle Armatures aus der Szene (z.B. aus GLB-Import).
    Meshes bleiben erhalten – für PoC wollen wir unser eigenes Rig hinzufügen.
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


def get_mesh_objects():
    """Gibt alle Mesh-Objekte (ohne Armature) zurück."""
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def get_armature_objects():
    """Gibt alle Armature-Objekte zurück."""
    return [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]


def enable_rigify():
    """Aktiviert das Rigify-Addon."""
    try:
        bpy.ops.preferences.addon_enable(module="rigify")
        return True
    except Exception:
        return False


def get_mesh_bounds(meshes):
    """Ermittelt die kombinierte Bounding-Box aller Meshes in World-Space."""
    from mathutils import Vector

    min_co = [float("inf")] * 3
    max_co = [float("-inf")] * 3
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

    # Rigify Human Meta-Rig hinzufügen (Operator von Rigify-Addon)
    try:
        bpy.ops.object.armature_human_metarig_add()
    except AttributeError:
        raise RuntimeError(
            "Rigify-Addon nicht aktiv oder object.armature_human_metarig_add nicht verfügbar"
        )
    metarig = bpy.context.active_object

    # Mesh-Bounds ermitteln für Skalierung
    meshes = get_mesh_objects()
    if not meshes:
        raise RuntimeError("Kein Mesh nach GLB-Import gefunden")

    min_co, max_co = get_mesh_bounds(meshes)
    center = [(min_co[i] + max_co[i]) / 2 for i in range(3)]
    size = [max_co[i] - min_co[i] for i in range(3)]
    height = max(size) if max(size) > 0 else 1.0

    # Meta-Rig positionieren und skalieren (Human ~2 Blender-Units)
    metarig.location = center
    scale = height / 2.0
    metarig.scale = (scale, scale, scale)
    bpy.ops.object.select_all(action="DESELECT")
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.transform_apply(location=True, scale=True, rotation=False)

    return metarig


def generate_rigify_rig(metarig):
    """Generiert das finale Rig aus dem Meta-Rig."""
    bpy.ops.object.select_all(action="DESELECT")
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.pose.rigify_generate()


def parent_mesh_with_auto_weights(mesh, armature):
    """Verknüpft Mesh mit Armature und berechnet Automatic Weights."""
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")


def export_glb(path: str):
    """Exportiert die Szene als GLB mit Armature."""
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Blender Rigging PoC")
    parser.add_argument("input_glb", help="Eingabe-GLB-Datei")
    parser.add_argument("output_glb", help="Ausgabe-GLB-Datei (geriggt)")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

    start_time = time.time()

    # 1. Szene leeren
    clear_scene()

    # 2. Rigify aktivieren
    if not enable_rigify():
        print("WARNUNG: Rigify konnte nicht aktiviert werden – nutze Basic-Armature")

    # 3. GLB importieren
    import_glb(args.input_glb)
    # Vorhandene Armatures entfernen (z.B. von bereits geriggten GLBs)
    remove_armatures_keep_meshes()
    meshes = get_mesh_objects()
    if not meshes:
        print("FEHLER: Kein Mesh in GLB gefunden")
        sys.exit(1)
    print(f"Importiert: {len(meshes)} Mesh(es)")

    # 4. Rigify Human Meta-Rig hinzufügen und anpassen
    metarig = add_rigify_human_metarig()

    # 5. Rig generieren
    generate_rigify_rig(metarig)
    armatures = get_armature_objects()
    if not armatures:
        print("FEHLER: Keine Armature nach Rigify-Generierung")
        sys.exit(1)
    rig = [a for a in armatures if a != metarig][0] if len(armatures) > 1 else armatures[0]

    # 6. Meshes mit Automatic Weights parenten
    for mesh in meshes:
        parent_mesh_with_auto_weights(mesh, rig)

    # 7. Meta-Rig entfernen (nur finales Rig exportieren)
    bpy.ops.object.select_all(action="DESELECT")
    if metarig.name in bpy.data.objects:
        metarig.select_set(True)
        bpy.ops.object.delete()

    # 8. Export
    export_glb(args.output_glb)

    elapsed = time.time() - start_time
    print(f"Rigging abgeschlossen in {elapsed:.1f}s")
    print(f"Output: {args.output_glb}")


if __name__ == "__main__":
    main()
