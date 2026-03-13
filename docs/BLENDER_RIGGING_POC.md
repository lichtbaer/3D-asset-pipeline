# Blender Headless Rigging PoC – SMA-172

## Übersicht

Technische Validierung: Kann Blender headless im Docker-Container einen realistischen Charakter-Mesh automatisch riggen?

## Setup

### Blender-Container

```bash
# Image bauen
docker compose --profile tools build blender

# Blender-Version prüfen
docker compose --profile tools run --rm blender --version
```

### Rigging-Script ausführen

```bash
# Mit Test-Mesh (CesiumMan aus glTF-Sample-Models)
./scripts/run_blender_rig_test.sh storage/meshes/test_human.glb storage/meshes/test_human_rigged.glb
```

Oder direkt mit Docker:

```bash
docker compose --profile tools run --rm blender \
  --background \
  --python /workspace/scripts/blender_rig_test.py \
  -- /workspace/storage/meshes/input.glb /workspace/storage/meshes/output_rigged.glb
```

## Ablauf des Scripts

1. **GLB importieren** (`bpy.ops.import_scene.gltf`)
2. **Vorhandene Armatures entfernen** (falls GLB bereits geriggt)
3. **Rigify aktivieren** (Addon)
4. **Rigify Human Meta-Rig hinzufügen** (`object.armature_human_metarig_add`)
5. **Meta-Rig an Mesh-Größe anpassen** (Skalierung an Bounding-Box)
6. **Rig generieren** (`pose.rigify_generate`)
7. **Automatic Weights** (`object.parent_set(type='ARMATURE_AUTO')`)
8. **GLB exportieren** mit Armature

## Test-Meshes

- `storage/meshes/test_human.glb` – CesiumMan (Khronos glTF-Sample-Models)
- Weitere Purzel-Meshes aus Mesh-Generierung (Hunyuan3D, TripoSR, etc.) können verwendet werden

## Qualitätsbefund

**Tests ausführen:**

```bash
# 1. Test-Meshes laden
./scripts/download_test_meshes.sh

# 2. Blender-Image bauen
docker compose --profile tools build blender

# 3. Blender-Version prüfen
docker compose --profile tools run --rm blender --version

# 4. Rigging-Test mit CesiumMan
./scripts/run_blender_rig_test.sh storage/meshes/test_human.glb storage/meshes/test_human_rigged.glb

# 5. Optional: Weitere Meshes (z.B. aus Purzel Mesh-Generierung)
# ./scripts/run_blender_rig_test.sh storage/meshes/<job_id>.glb storage/meshes/<job_id>_rigged.glb
```

**Befund-Tabelle (nach Tests ausfüllen):**

| Kriterium | Ergebnis |
|-----------|----------|
| Blender headless läuft | |
| Mesh korrekt erkannt | |
| Auto-Weight-Painting brauchbar | |
| Laufzeit pro Job (Sekunden) | |
| Mesh-Qualitäten: funktioniert / funktioniert nicht | |

## Entscheidungsgrundlage

- ✅ Brauchbar → SMA-171-analog für Blender anlegen
- ⚠️ Brauchbar mit Einschränkungen → dokumentieren was fehlt
- ❌ Nicht brauchbar → begründen warum

## Technische Details

### Container-Optionen (bewertet)

| Option | Bewertung |
|--------|-----------|
| `apt install blender` im API-Container | ❌ Debian liefert Blender 3.x, kein 4.x LTS |
| Separater Service mit Tarball (gewählt) | ✅ Blender 4.2 LTS, ~400MB, sauber getrennt |
| `blenderkit/headless-blender:blender-4.2` | ⚠️ ~800MB, inkl. X11/VNC (für PoC überdimensioniert) |

### Gewählte Lösung

- **Blender:** 4.2 LTS (Tarball von blender.org)
- **Basis:** Debian Bookworm Slim
- **Image-Größe:** ~400MB (vs. blenderkit ~800MB)
