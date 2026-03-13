#!/bin/bash
# Lädt Test-Meshes für den Blender Rigging PoC (SMA-172)
set -e

MESH_DIR="$(cd "$(dirname "$0")/.." && pwd)/storage/meshes"
mkdir -p "$MESH_DIR"

echo "Lade Test-Meshes nach $MESH_DIR ..."

# CesiumMan – humanoides Khronos glTF-Sample-Model (bereits geriggt, Script entfernt Armature)
if [ ! -f "$MESH_DIR/test_human.glb" ]; then
  curl -sL -o "$MESH_DIR/test_human.glb" \
    "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/main/2.0/CesiumMan/glTF-Binary/CesiumMan.glb"
  echo "  ✓ test_human.glb (CesiumMan)"
else
  echo "  - test_human.glb bereits vorhanden"
fi

# Box – einfaches ungeriggtes Mesh (Fallback-Test)
if [ ! -f "$MESH_DIR/test_box.glb" ]; then
  curl -sL -o "$MESH_DIR/test_box.glb" \
    "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/main/2.0/Box/glTF-Binary/Box.glb"
  echo "  ✓ test_box.glb (Box)"
else
  echo "  - test_box.glb bereits vorhanden"
fi

echo "Fertig."
