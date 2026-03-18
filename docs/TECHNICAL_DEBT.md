# Technical Debt Audit

Erstellt: 2026-03-15

## Behobene Befunde

#### ~~1. Stille Exception-Unterdrueckung~~ (behoben)
Alle `except Exception: pass` Stellen loggen jetzt via `logger.debug()` bzw. `print(..., file=sys.stderr)`.

#### ~~3. Duplizierte Blender-Skripte~~ (behoben)
PoC-Duplikate in `scripts/` entfernt. Produktionsversionen verbleiben in `api/scripts/`.

#### ~~4. Deprecated config/models.py~~ (behoben)
Leere Datei `api/app/config/models.py` geloescht. `model_key` bleibt vorerst — wird aktiv vom Frontend genutzt.

#### ~~5. Settings-Klasse nicht Pydantic-basiert~~ (behoben)
`api/app/core/config.py` auf `pydantic_settings.BaseSettings` migriert mit `.env`-Support und Validierung.

#### ~~9. console.error() im Frontend~~ (behoben)
`console.error` in `MeshViewer.tsx` und `AnimationMeshViewer.tsx` durch `console.warn` ersetzt.

#### ~~12. Kein API-Versioning~~ (behoben)
Alle API-Endpoints unter `/api/v1/` Prefix. Health-Endpoint und Static-Mounts bleiben ohne Prefix.

#### ~~13. CORS allow_headers zu permissiv~~ (behoben)
`allow_headers` auf `["Content-Type", "Authorization"]` eingeschraenkt.

#### ~~14. Error-Handling-Duplikation in Orchestrierungs-Services~~ (behoben)
Alle 5 Orchestrierungsfunktionen (mesh, rigging, animation, image, bgremoval) hatten nahezu identische try-except-Bloecke.
Zentraler `handle_provider_errors()` Context Manager in `api/app/services/job_error_handler.py` eingefuehrt.

#### ~~15. Magic Strings fuer Job-Status~~ (behoben)
Status-Werte `"pending"`, `"processing"`, `"done"`, `"failed"` waren als Strings ueberall verstreut.
`JobStatus` StrEnum in `api/app/models/enums.py` eingefuehrt und in allen Services verwendet.

#### ~~16. Lose Callback-Typisierung~~ (behoben)
`Callable[..., Awaitable[None]]` Typ-Aliase verloren alle Typinformationen.
Typsicheres `UpdateJobCallback` Protocol in `api/app/services/job_error_handler.py` eingefuehrt.

#### ~~17. AssetMetadata als plain Python-Klasse~~ (behoben)
`AssetMetadata` mit 17 Init-Parametern und manuellem `to_dict()` auf Pydantic `BaseModel` migriert.
Automatische Validierung, Serialisierung und reduzierter Boilerplate.

---

## Offene Befunde

### Hoch

#### 2. Frontend-Testabdeckung
Nur 3 Testdateien (`agents.test.ts`, `useChat.test.ts`, `useAssetFromUrl.test.tsx`) bei ca. 100 Komponenten.

**Empfehlung:** Tests fuer kritische Komponenten priorisieren:
- `AssetDetailModal`
- `SketchfabImportModal`
- `PipelineStepper`
- Job-Status-Komponenten

---

### Mittel

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
`api/app/routers/assets.py` speichert Texture-Baking-Jobs in einem `dict` im Speicher. State geht bei Server-Neustart verloren.

**Empfehlung:** In die Datenbank (GenerationJob) migrieren.

#### 4b. model_key Deprecation (offen)
`model_key` in `api/app/models/generation_job.py:23` als deprecated markiert, aber noch vom Frontend aktiv genutzt (8 Dateien). Backward-Compat-Mapping in `api/app/schemas/generation.py:17-46`.

**Empfehlung:** Frontend auf `provider_key` umstellen, dann `model_key` entfernen.

---

### Niedrig

#### 10. `type: ignore` in main.py
`api/app/main.py:35` hat `# type: ignore[arg-type]` fuer `_rate_limit_exceeded_handler`. Bekannte slowapi-Limitation.

#### 11. Print-Logging in Blender-Skripten
2 Skripte in `api/scripts/` mit `print()`-Aufrufen statt `logging.getLogger()`.

**Empfehlung:** Akzeptabel fuer Blender-Subprozesse.

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
- API-Versioning unter `/api/v1/` (neu)
- Pydantic-basierte Settings mit `.env`-Support (neu)
- Zentralisiertes Error-Handling via Context Manager (neu)
- JobStatus StrEnum statt Magic Strings (neu)
- Typsichere Callback-Protokolle (neu)
- AssetMetadata als Pydantic BaseModel (neu)
