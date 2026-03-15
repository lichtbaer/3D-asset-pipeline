# Technical Debt Audit

Erstellt: 2026-03-15

## Befunde nach Prioritaet

### Hoch

#### 1. Stille Exception-Unterdrueckung
8 Stellen mit `except Exception: pass` — Fehler werden verschluckt, Debugging wird erschwert.

| Datei | Zeile |
|-------|-------|
| `api/app/database.py` | 43 |
| `api/app/services/sketchfab_service.py` | 105 |
| `api/app/services/image_providers/picsart.py` | 124 |
| `api/app/services/bgremoval_providers/picsart.py` | 77 |
| `scripts/blender_rig_test.py` | 58 |
| `scripts/blender_rig_human.py` | 62 |
| `api/scripts/blender_rig_human.py` | 62 |

**Empfehlung:** `logger.exception()` vor `pass` einfuegen oder spezifischere Exceptions fangen.

#### 2. Frontend-Testabdeckung
Nur 3 Testdateien (`agents.test.ts`, `useChat.test.ts`, `useAssetFromUrl.test.tsx`) bei ca. 100 Komponenten.

**Empfehlung:** Tests fuer kritische Komponenten priorisieren:
- `AssetDetailModal`
- `SketchfabImportModal`
- `PipelineStepper`
- Job-Status-Komponenten

---

### Mittel

#### 3. Duplizierte Blender-Skripte
Nahezu identische Kopien in zwei Verzeichnissen:
- `scripts/blender_rig_test.py` ↔ `api/scripts/blender_rig_human.py`
- `scripts/blender_bake_textures.py` ↔ `api/scripts/blender_bake_textures.py`

**Empfehlung:** Konsolidieren — ein zentrales Verzeichnis, aus dem sowohl API als auch CLI referenzieren.

#### 4. Deprecations nicht aufgeraeumt
- `api/app/config/models.py` enthaelt nur einen Deprecation-Kommentar (leere Datei)
- `model_key` in `api/app/models/generation_job.py:23` als deprecated markiert, aber noch im Schema mit Backward-Compat-Mapping (`api/app/schemas/generation.py:17-46`)

**Empfehlung:**
- Leere `config/models.py` loeschen
- Migration-Timeline fuer `model_key`-Entfernung definieren

#### 5. Settings-Klasse nicht Pydantic-basiert
`api/app/core/config.py` verwendet plain `os.getenv()` statt `pydantic_settings.BaseSettings`. Keine Validierung, kein `.env`-Auto-Loading.

**Empfehlung:** Auf `pydantic_settings.BaseSettings` migrieren.

#### 6. Uebergrosse Komponenten und Services
Mehrere Dateien sind zu gross und sollten aufgeteilt werden:

| Datei | Zeilen | Prioritaet |
|-------|--------|------------|
| `frontend/src/pages/PipelinePage.tsx` | 1.369 | Kritisch |
| `frontend/src/pages/AssetLibrary.tsx` | 861 | Kritisch |
| `frontend/src/components/assets/AssetDetailModal.tsx` | 829 | Kritisch |
| `api/app/routers/generation.py` | 1.019 | Hoch |
| `api/app/services/asset_service.py` | 962 | Hoch |
| `api/app/routers/assets.py` | 798 | Hoch |

**Empfehlung:** Logik in Sub-Komponenten/Sub-Services extrahieren.

#### 7. Backend Coverage-Omits
7 kritische Dateien sind von der Coverage-Messung ausgeschlossen (`pyproject.toml`):
- `app/main.py`, `app/routers/generation.py`, `app/services/mesh_generation.py`
- `app/services/animation_generation.py`, `app/services/bgremoval.py`
- `app/services/mesh_export_service.py`

**Empfehlung:** Omits schrittweise entfernen und Tests ergaenzen.

#### 8. In-Memory Job State (Texture Baking)
`api/app/services/job_service.py` speichert Texture-Baking-Jobs in einem `dict` im Speicher. State geht bei Server-Neustart verloren.

**Empfehlung:** In die Datenbank (GenerationJob) migrieren.

---

### Niedrig

#### 9. console.error() im Frontend
`MeshViewer.tsx:191` und `AnimationMeshViewer.tsx:173` verwenden `console.error()` statt strukturiertem Logging.

**Empfehlung:** Error-Boundary mit Service-Anbindung einfuehren.

#### 10. `type: ignore` in main.py
`api/app/main.py:35` hat `# type: ignore[arg-type]` fuer `_rate_limit_exceeded_handler`.

**Empfehlung:** Typ-Annotation korrekt definieren oder slowapi-Typen pruefen.

#### 11. Print-Logging in Blender-Skripten
4 Skripte mit insgesamt ~24 `print()`-Aufrufen statt `logging.getLogger()`.

**Empfehlung:** Akzeptabel fuer CLI-Subprozesse, aber `logging` waere konsistenter.

#### 12. Kein API-Versioning
Alle Endpoints direkt unter `/generate`, `/assets` etc. ohne Versions-Prefix.

**Empfehlung:** `/api/v1/` Prefix einfuehren fuer zukuenftige Migrationen.

#### 13. CORS allow_headers zu permissiv
`api/app/main.py` setzt `allow_headers=["*"]` — sollte auf benoetigte Headers eingeschraenkt werden.

---

## Positiv-Befunde

- Gut strukturierte Exception-Hierarchie (`api/app/exceptions.py`)
- Provider-Pattern mit Base/Registry konsistent umgesetzt
- Security: API-Key-Auth, Path-Security, Security-Headers, CORS
- Keine hardcoded Secrets — alles ueber Environment-Variablen
- JSON-strukturiertes Logging mit Rotation im Backend
- Saubere `__all__`-Exports, keine Wildcard-Imports
- CI/CD vorhanden (`.github/workflows/test.yml`)
- 28 Backend-Testdateien mit guter Abdeckung
- Alembic-Migrationen ordentlich versioniert
