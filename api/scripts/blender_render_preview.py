#!/usr/bin/env python3
"""
Blender Headless Preview Render — PURZEL-FEAT-013

Rendert ein 512×512 PNG-Vorschaubild eines GLB-Assets via EEVEE.
Neutrale Studio-Beleuchtung, isometrische 3/4-Kamera-Perspektive.

Aufruf:
  blender --background --python scripts/blender_render_preview.py -- \\
    input.glb output.png [width] [height]
"""
import argparse
import math
import sys
import os

import bpy
from mathutils import Vector


def clear_scene() -> None:
    """Löscht alle Objekte und Lichter in der Szene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in bpy.data.collections:
        bpy.data.collections.remove(coll)


def import_glb(path: str) -> list:
    """Importiert GLB-Datei, gibt alle importierten Objekte zurück."""
    bpy.ops.import_scene.gltf(filepath=path)
    return list(bpy.context.scene.objects)


def get_scene_bounds(objects: list) -> tuple[Vector, float]:
    """Gibt Mittelpunkt und Radius der Bounding Box aller Objekte zurück."""
    min_corner = Vector((float("inf"),) * 3)
    max_corner = Vector((float("-inf"),) * 3)
    found = False
    for obj in objects:
        if obj.type not in ("MESH", "EMPTY"):
            continue
        for corner in [Vector(obj.bound_box[i]) for i in range(8)]:
            world_corner = obj.matrix_world @ corner
            min_corner = Vector(min(a, b) for a, b in zip(min_corner, world_corner))
            max_corner = Vector(max(a, b) for a, b in zip(max_corner, world_corner))
            found = True
    if not found:
        return Vector((0, 0, 0)), 1.0
    center = (min_corner + max_corner) / 2
    radius = (max_corner - min_corner).length / 2
    return center, max(radius, 0.01)


def setup_camera(center: Vector, radius: float) -> object:
    """Positioniert Kamera in 3/4-isometrischer Perspektive."""
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    bpy.context.scene.camera = cam

    # 3/4 isometrische Position: von vorne-oben-rechts
    distance = radius * 3.5
    angle_h = math.radians(45)  # horizontal
    angle_v = math.radians(30)  # vertikal

    x = center.x + distance * math.cos(angle_v) * math.sin(angle_h)
    y = center.y - distance * math.cos(angle_v) * math.cos(angle_h)
    z = center.z + distance * math.sin(angle_v)

    cam.location = Vector((x, y, z))

    # Kamera auf Mittelpunkt ausrichten
    direction = center - cam.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam.rotation_euler = rot_quat.to_euler()

    cam.data.lens = 50
    return cam


def setup_lighting(center: Vector, radius: float) -> None:
    """Drei-Punkt-Studio-Beleuchtung."""
    lights = [
        # Key light (Hauptlicht, von vorne-oben-links)
        {"type": "AREA", "energy": 500 * radius, "size": radius * 2,
         "offset": ((-radius * 2, -radius * 2, radius * 3))},
        # Fill light (Fülllicht, von rechts)
        {"type": "AREA", "energy": 200 * radius, "size": radius * 1.5,
         "offset": ((radius * 3, -radius, radius * 2))},
        # Rim light (Gegenlicht, von hinten)
        {"type": "AREA", "energy": 300 * radius, "size": radius * 1,
         "offset": ((0, radius * 3, radius * 1))},
    ]
    for light_cfg in lights:
        bpy.ops.object.light_add(type=light_cfg["type"])
        light = bpy.context.object
        light.location = center + Vector(light_cfg["offset"])
        light.data.energy = light_cfg["energy"]
        if hasattr(light.data, "size"):
            light.data.size = light_cfg["size"]
        # Licht auf Mittelpunkt ausrichten
        direction = center - light.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        light.rotation_euler = rot_quat.to_euler()


def setup_render(width: int, height: int, output_path: str) -> None:
    """Konfiguriert EEVEE-Renderer für schnelles Rendering."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.context.scene.eevee, "use_bloom") else "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    # Hintergrund transparent
    scene.render.film_transparent = True

    # EEVEE-Qualitätseinstellungen
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 64
        if hasattr(scene.eevee, "use_gtao"):
            scene.eevee.use_gtao = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Blender Preview Render")
    parser.add_argument("input_glb", help="Input GLB-Datei")
    parser.add_argument("output_png", help="Output PNG-Datei")
    parser.add_argument("width", type=int, default=512, nargs="?", help="Breite in Pixeln")
    parser.add_argument("height", type=int, default=512, nargs="?", help="Höhe in Pixeln")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

    input_path = args.input_glb
    output_path = args.output_png
    width = max(64, min(2048, args.width))
    height = max(64, min(2048, args.height))

    if not os.path.isfile(input_path):
        print(f"FEHLER: Input nicht gefunden: {input_path}", file=sys.stderr)
        return 1

    clear_scene()
    objects = import_glb(input_path)

    if not any(o.type == "MESH" for o in objects):
        print("FEHLER: GLB enthält keine Meshes", file=sys.stderr)
        return 1

    center, radius = get_scene_bounds(objects)
    setup_camera(center, radius)
    setup_lighting(center, radius)
    setup_render(width, height, output_path)

    bpy.ops.render.render(write_still=True)

    if not os.path.isfile(output_path):
        print("FEHLER: Render hat keine Output-Datei erzeugt", file=sys.stderr)
        return 1

    print(f"Vorschau gerendert: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
