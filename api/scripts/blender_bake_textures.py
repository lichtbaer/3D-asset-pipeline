#!/usr/bin/env python3
"""
Blender Headless Texture Baking – PURZEL-041 (SMA-197)

Baked PBR-Texturen vom High-Poly-Mesh auf Low-Poly-Mesh via Raycast-Projektion.
Nach Mesh-Simplification gehen UVs verloren – dieses Script rebaked die Texturen.

Aufruf:
  blender --background --python scripts/blender_bake_textures.py -- \\
    source.glb target.glb output.glb 1024 diffuse,roughness,metallic

Bake-Typen: diffuse (Base Color), roughness, metallic (Metallic als Graustufen-Workaround)
"""
import argparse
import sys
import os

# Blender-Python: bpy wird vom Blender-Interpreter bereitgestellt
import bpy


def clear_scene() -> None:
    """Löscht alle Objekte in der Szene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_glb(path: str) -> list:
    """Importiert GLB-Datei, gibt Liste der importierten Mesh-Objekte zurück."""
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def get_all_meshes() -> list:
    """Gibt alle Mesh-Objekte in der Szene zurück."""
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def select_objects(obj_list: list, select: bool = True) -> None:
    """Wählt/deselektiert Objekte."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in obj_list:
        obj.select_set(select)


def uv_smart_project(obj_list: list) -> None:
    """UV-Unwrap mit Smart Project auf die angegebenen Objekte."""
    select_objects(obj_list)
    bpy.context.view_layer.objects.active = obj_list[0] if obj_list else None
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def create_bake_image(name: str, resolution: int) -> object:
    """Erstellt eine neue Blender-Image-Textur für Baking."""
    img = bpy.data.images.new(
        name=name,
        width=resolution,
        height=resolution,
        alpha=True,
        float_buffer=False,
    )
    return img


def setup_material_for_bake(
    obj: object,
    bake_type: str,
    img: object,
    uv_layer_name: str = "UVMap",
) -> None:
    """
    Erstellt/aktualisiert Material mit Image-Texture-Node für den Bake-Typ.
    diffuse -> Base Color, roughness -> Roughness, metallic -> Metallic (Graustufen)
    """
    if obj.data.materials:
        mat = obj.data.materials[0]
    else:
        mat = bpy.data.materials.new(name=f"Baked_{bake_type}")
        obj.data.materials.append(mat)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output-Node
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)

    # Principled BSDF
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (200, 0)

    # Image-Texture-Node (Bake-Ziel)
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = img
    tex_node.location = (-200, 0)

    # UV-Map-Node
    uv_node = nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = uv_layer_name
    uv_node.location = (-400, 0)

    links.new(uv_node.outputs["UV"], tex_node.inputs["Vector"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    if bake_type == "diffuse":
        links.new(tex_node.outputs["Color"], principled.inputs["Base Color"])
    elif bake_type == "roughness":
        links.new(tex_node.outputs["Color"], principled.inputs["Roughness"])
    elif bake_type == "metallic":
        # Metallic erwartet einzelne Graustufe – Color zu Value
        separate = nodes.new("ShaderNodeSeparateColor")
        separate.location = (0, 0)
        links.new(tex_node.outputs["Color"], separate.inputs["Color"])
        links.new(separate.outputs["Red"], principled.inputs["Metallic"])
    else:
        links.new(tex_node.outputs["Color"], principled.inputs["Base Color"])


def run_bake(
    source_objects: list,
    target_objects: list,
    bake_type: str,
    resolution: int,
) -> object:
    """
    Führt Baking für einen Typ durch. Gibt die gebackene Image zurück.
    """
    img = create_bake_image(f"bake_{bake_type}", resolution)

    for obj in target_objects:
        setup_material_for_bake(obj, bake_type, img)

    # Bake-Typ auf Blender-API mappen
    blender_type = "DIFFUSE"
    if bake_type == "roughness":
        blender_type = "ROUGHNESS"
    elif bake_type == "metallic":
        blender_type = "DIFFUSE"  # Metallic als Base Color Graustufe darstellen

    bpy.context.scene.render.engine = "CYCLES"
    if hasattr(bpy.context.scene, "cycles"):
        bpy.context.scene.cycles.device = "CPU"

    # Pro Target-Mesh: Source selected, Target active (Selected to Active)
    for target_obj in target_objects:
        select_objects(source_objects)
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj

        if target_obj.data.materials and target_obj.data.materials[0].use_nodes:
            mat = target_obj.data.materials[0]
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image == img:
                    mat.node_tree.nodes.active = node
                    break

        bpy.ops.object.bake(
            type=blender_type,
            use_selected_to_active=True,
            cage_extrusion=0.1,
            max_ray_distance=0.0,
            margin=16,
        )

    return img


def export_glb(path: str, obj_list: list) -> None:
    """Exportiert ausgewählte Objekte als GLB mit eingebetteten Texturen."""
    select_objects(obj_list)
    bpy.ops.export_scene.gltf(
        filepath=path,
        use_selection=True,
        export_format="GLB",
        export_materials="EXPORT",
        export_textures=True,
        export_image_format="AUTO",
        export_apply=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Blender Texture Baking: High-Poly -> Low-Poly"
    )
    parser.add_argument("source_glb", help="High-Poly-Mesh mit PBR-Texturen")
    parser.add_argument("target_glb", help="Low-Poly-Mesh (Ziel für Bake)")
    parser.add_argument("output_glb", help="Output-GLB mit gebackenen Texturen")
    parser.add_argument(
        "resolution",
        type=int,
        default=1024,
        nargs="?",
        help="Textur-Auflösung (512, 1024, 2048)",
    )
    parser.add_argument(
        "bake_types",
        type=str,
        default="diffuse,roughness,metallic",
        nargs="?",
        help="Komma-getrennt: diffuse,roughness,metallic",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

    source_path = args.source_glb
    target_path = args.target_glb
    output_path = args.output_glb
    resolution = max(256, min(4096, args.resolution))
    bake_types = [t.strip().lower() for t in args.bake_types.split(",") if t.strip()]

    if not bake_types:
        bake_types = ["diffuse", "roughness", "metallic"]

    if not os.path.isfile(source_path):
        print(f"FEHLER: Source nicht gefunden: {source_path}", file=sys.stderr)
        return 1
    if not os.path.isfile(target_path):
        print(f"FEHLER: Target nicht gefunden: {target_path}", file=sys.stderr)
        return 1

    clear_scene()

    # 1. Source importieren (High-Poly mit Texturen)
    source_meshes = import_glb(source_path)
    if not source_meshes:
        print("FEHLER: Source-GLB enthält keine Meshes", file=sys.stderr)
        return 1

    source_set = set(source_meshes)

    # 2. Target importieren (Low-Poly) – fügt zur Szene hinzu
    import_glb(target_path)
    target_meshes = [o for o in get_all_meshes() if o not in source_set]
    if not target_meshes:
        print("FEHLER: Target-GLB enthält keine Meshes", file=sys.stderr)
        return 1

    # 3. UV-Unwrap auf Target
    uv_smart_project(target_meshes)

    # 4. Baking pro Typ
    for bake_type in bake_types:
        if bake_type not in ("diffuse", "roughness", "metallic"):
            continue
        try:
            run_bake(source_meshes, target_meshes, bake_type, resolution)
        except Exception as e:
            print(f"Warnung: Bake {bake_type} fehlgeschlagen: {e}", file=sys.stderr)

    # 5. Export mit eingebetteten Texturen
    export_glb(output_path, target_meshes)

    if not os.path.isfile(output_path):
        print("FEHLER: Output-GLB wurde nicht erstellt", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
