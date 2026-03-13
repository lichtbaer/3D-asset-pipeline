#!/bin/bash
# Blender Rigging PoC – SMA-172
# Aufruf: ./scripts/run_blender_rig_test.sh input.glb output_rigged.glb
# Pfade relativ zu Projektroot (z.B. storage/meshes/input.glb)

set -e
INPUT="${1:?Usage: $0 input.glb output_rigged.glb}"
OUTPUT="${2:?Usage: $0 input.glb output_rigged.glb}"

# Im Container: Projektroot ist /workspace gemountet
# Pfade relativ zu Projektroot (z.B. storage/meshes/input.glb)
INPUT_ABS="/workspace/$(echo "$INPUT" | sed 's|^\./||')"
OUTPUT_ABS="/workspace/$(echo "$OUTPUT" | sed 's|^\./||')"

docker compose --profile tools run --rm blender \
  --background \
  --python /workspace/scripts/blender_rig_test.py \
  -- "$INPUT_ABS" "$OUTPUT_ABS"
