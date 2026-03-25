# Technical Debt Audit

Erstellt: 2026-03-15 · **Letzte Code-Prüfung der offenen Punkte: 2026-03-25**

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

#### ~~18. Duplizierte Error-Extraktion im Frontend~~ (behoben)
Fehler-Extraktion aus Axios-Responses war 3x dupliziert (AssetUploadZone, useChat, PromptAssistant).
Zentralisiert in `frontend/src/utils/errorUtils.ts` (`extractErrorMessage`).

#### ~~19. Duplizierte Job-Retry- und URL-Logik~~ (behoben)
Fast identische Retry-Funktionen und URL-Konstruktion in 4 API-Modulen (animation, bgremoval, mesh, rigging).
Extrahiert in `frontend/src/api/utils.ts` (`createRetryFn`, `toAbsoluteUrl`).

#### ~~20. Fehlende ErrorBoundary~~ (behoben)
`App.tsx` hatte keine React ErrorBoundary. Unbehandelte Render-Fehler fuehrten zu leerer Seite.
`ErrorBoundary`-Komponente in `frontend/src/components/ErrorBoundary.tsx` hinzugefuegt.

#### ~~21. Stille Fehler in AssetDetailModal~~ (behoben)
`saveMeta()`, `handleStepDeleteClick()` und `handleStepDeleteConfirm()` ignorierten Fehler.
Jetzt werden Toast-Benachrichtigungen bei Fehler angezeigt.

#### ~~22. Chat-SessionStorage ohne Debounce~~ (behoben)
`useChat` schrieb bei jeder Nachricht sofort in sessionStorage. Jetzt mit 500ms Debounce und
Begrenzung auf max. 50 gespeicherte Nachrichten.

#### ~~23. Duplizierter AssetStepData-Typ~~ (behoben)
`AssetStepData` war in `AssetDetailModal.tsx` lokal definiert, obwohl `assets.ts` einen generischen
`Record<string, unknown>` fuer Steps nutzte. Konkreten `AssetStepData`-Typ in `assets.ts` definiert
und in AssetDetailModal importiert.

#### ~~24. npm audit fehlte in CI~~ (behoben)
Backend hatte `pip-audit` in der CI-Pipeline, Frontend nicht. `npm audit --audit-level=high`
als CI-Schritt im Frontend-Job hinzugefuegt.

---

## Offene Befunde

*Nachstehende Einschaetzungen wurden am **2026-03-25** gegen den aktuellen Stand im Repo geprueft (Zeilenzahlen: `wc -l`, Frontend-Tests: `frontend/src/__tests__/`, Backend: `api/pyproject.toml` + `api/app/routers/assets.py`).*

### Hoch

#### 2. Frontend-Testabdeckung
Weiterhin **3** Vitest-Dateien unter `frontend/src/__tests__/` (`agents.test.ts`, `useChat.test.ts`, `useAssetFromUrl.test.tsx`); die Zahl der Komponenten/Seiten ist gross — die relative Unterversorgung bleibt.

**Empfehlung:** Tests fuer kritische Komponenten priorisieren:
- `AssetDetailModal`
- `SketchfabImportModal`
- `PipelineStepper`
- Job-Status-Komponenten

---

### Mittel

#### 6. Uebergrosse Komponenten und Services
Mehrere Dateien sind zu gross und sollten aufgeteilt werden (Stand 2026-03-25):

| Datei | Zeilen | Prioritaet |
|-------|--------|------------|
| `frontend/src/pages/PipelinePage.tsx` | ~1.411 | Kritisch |
| `frontend/src/pages/AssetLibrary.tsx` | ~862 | Kritisch |
| `frontend/src/components/assets/AssetDetailModal.tsx` | ~832 | Kritisch |
| `api/app/routers/generation.py` | ~1.071 | Hoch |
| `api/app/services/asset_service.py` | ~923 | Hoch |
| `api/app/routers/assets.py` | ~810 | Hoch |

**Empfehlung:** Logik in Sub-Komponenten/Sub-Services extrahieren.

#### 7. Backend Coverage-Omits
In `api/pyproject.toml` sind **deutlich mehr** Pfade von Coverage ausgeschlossen als frueher nur unter „7 Dateien“ subsumiert. Auszug (vollstaendige Liste siehe `[tool.coverage.run] omit`):

- Kern/Orchestrierung: `app/main.py`, `app/logging_config.py`, `app/database.py`
- Router: `app/routers/generation.py`, `app/routers/sketchfab.py`, `app/routers/storage.py`
- Services: u. a. `mesh_generation.py`, `animation_generation.py`, `rigging_generation.py`, `bgremoval.py`, `mesh_export_service.py`
- Provider-Bloecke: `app/services/bgremoval_providers/*`, `app/services/image_providers/picsart.py`, `app/providers/animation/*`, `app/providers/rigging/blender_rigify.py`, `app/providers/rigging/unirig_local.py`
- Sonstiges: `alembic/*`, `*/__init__.py`

**Empfehlung:** Omits schrittweise entfernen und Tests ergaenzen; technische Schuld ist hier **groesser** als die alte „7-Dateien“-Formulierung suggerierte.

#### 8. In-Memory Job State (Texture Baking)
**Weiterhin aktuell:** `api/app/routers/assets.py` nutzt `_texture_bake_jobs: dict[str, dict[str, Any]]` (Zeilenbereich ~87 ff.); Status laeuft nur im Prozessspeicher, Neustart verwirft offene Jobs.

**Empfehlung:** In die Datenbank (z. B. eigenes Job-Modell oder Erweiterung von `GenerationJob`) migrieren.

#### 4b. model_key Deprecation (offen)
**Teilweise entschaerft im Frontend, API-Schicht bleibt:** Spalte `model_key` in `api/app/models/generation_job.py` weiterhin deprecated (nullable Alias). Im Frontend tritt `model_key` praktisch nur noch in `frontend/src/api/generation.ts` auf (optional + Fallback `provider_key ?? model_key`). **Nicht** mehr „8 Frontend-Dateien“. Backend: `api/app/schemas/generation.py` (Compat + `resolve_provider_and_params`), `api/app/routers/generation.py` (u. a. Deprecation-Header `X-Deprecated`, Lesen `job.model_key`).

**Empfehlung:** API-Clients und Responses konsequent auf `provider_key` umstellen, Legacy-Felder und Mapping nach Migration entfernen.

---

### Niedrig

#### 10. `type: ignore` in main.py
**Weiterhin aktuell:** `api/app/main.py` Zeile ~35 — `# type: ignore[arg-type]` fuer `_rate_limit_exceeded_handler`. Bekannte slowapi-Limitation.

#### 11. Print-Logging in Blender-Skripten
**Weiterhin aktuell:** `api/scripts/blender_rig_human.py` und `api/scripts/blender_bake_textures.py` nutzen `print()` (teilweise `file=sys.stderr`).

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
- **23** Testdateien (`test_*.py`) unter `api/tests/`; **28** Python-Dateien inkl. `conftest.py` und `__init__.py` (Stand 2026-03-25)
- Alembic-Migrationen ordentlich versioniert
- API-Versioning unter `/api/v1/` (neu)
- Pydantic-basierte Settings mit `.env`-Support (neu)
- Zentralisiertes Error-Handling via Context Manager (neu)
- JobStatus StrEnum statt Magic Strings (neu)
- Typsichere Callback-Protokolle (neu)
- AssetMetadata als Pydantic BaseModel (neu)
