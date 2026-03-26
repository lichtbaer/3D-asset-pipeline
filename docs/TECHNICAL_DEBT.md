# Technical Debt Audit

Erstellt: 2026-03-15 · **Letzte Code-Prüfung der offenen Punkte: 2026-03-26** · **Behebungsplan ergänzt: 2026-03-25** · **Prioritäten teilweise umgesetzt: 2026-03-26**

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

#### ~~25. Texture-Bake-Jobs persistent~~ (behoben)
Tabelle `texture_bake_job`, ORM `TextureBakeJob`, Router `assets.py` nutzt AsyncSession statt In-Memory-Dict.
Alembic: `20260325120000_texture_bake_job_drop_model_key.py`. CI: Postgres-Service + `alembic upgrade head` vor pytest.

#### ~~26. generation_job.model_key Spalte entfernt~~ (behoben)
Spalte `model_key` aus `generation_job` per derselben Migration entfernt. `ImageJobStatusResponse` liefert nur noch `provider_key`.
Frontend `generation.ts` ohne `model_key`-Typ/Fallback. **Verbleibend:** `ImageGenerateRequest.model_key` + `resolve_provider_and_params` fuer **eingehende** Alt-JSON-Requests; Header `X-Deprecated` bei POST mit `model_key`.

#### ~~27. Tote Frontend-Komponenten (Duplikate)~~ (behoben)
Vier Dateien in `frontend/src/components/pipeline/` waren unbenutzt — aeltere Versionen, die durch erweiterte
Implementierungen in `pipeline/rigging/` und `pipeline/animation/` ersetzt wurden:
`RiggingForm.tsx`, `RiggingJobStatus.tsx`, `AnimationForm.tsx`, `AnimationJobStatus.tsx` geloescht.

#### ~~28. Duplizierte `_extract_asset_id_from_url`~~ (behoben)
Identische Funktion existierte in `api/app/routers/generation.py` und `api/app/services/job_service.py`.
Konsolidiert: kanonische Definition in `job_service.py` (umbenannt zu `extract_asset_id_from_url`),
Import in `generation.py`.

#### ~~29. Callback-Alias-Duplikation in generation.py~~ (behoben)
`_update_mesh_job` und `_update_rigging_job` waren Aliase fuer `_update_glb_job`. Aliase entfernt,
alle Aufrufstellen nutzen direkt `_update_glb_job`.

#### ~~30. Breite `except Exception`-Klauseln~~ (behoben)
29 Stellen mit `except Exception` im Backend auf spezifische Typen umgestellt
(`httpx.HTTPStatusError`, `httpx.RequestError`, `OSError`, `ValueError`, `json.JSONDecodeError`, etc.).
Verbleibend: 1 bewusster Catch-All in `job_error_handler.py` (dokumentiert) und 2 Stellen in
Provider-Wrappern (`hf_inference.py`, `replicate_provider.py`) wo externe SDKs unvorhersehbare
Exception-Typen werfen.

#### ~~31. Schwache TypeScript-Typisierung `Record<string, unknown>`~~ (behoben)
24+ Stellen mit `Record<string, unknown>` in Frontend-API-Clients und Komponenten durch spezifische
Interfaces ersetzt (`ProviderParams`, `ImageGenerationParams`, `MeshProviderParams`, etc.) oder durch
den restriktiveren Typ `Record<string, string | number | boolean | null>` fuer dynamische Provider-Parameter.

---

## Offene Befunde

*Nachstehende Einschaetzungen wurden am **2026-03-25** gegen den aktuellen Stand im Repo geprueft; Zahlen zu Tests siehe aktuelle `frontend/src/__tests__/` und `api/tests/`.*

### Hoch

#### 2. Frontend-Testabdeckung
**4** Testdateien unter `frontend/src/__tests__/` (u. a. `PipelineStepper.test.tsx` neu); die Zahl der Komponenten bleibt gross — weiter ausbauen.

**Empfehlung:** Tests fuer kritische Komponenten priorisieren:
- `AssetDetailModal`
- `SketchfabImportModal`
- ~~`PipelineStepper`~~ (Basis-Tests vorhanden)
- Job-Status-Komponenten (`JobStatus`, `JobErrorBlock`)

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

#### ~~8. In-Memory Job State (Texture Baking)~~ → siehe Befund ~~25~~ (behoben)

#### 4b. model_key in **Request**-Body (optional, Restarbeit)
**Erledigt fuer DB und Job-Status-Response:** keine Spalte mehr, kein `model_key` in `ImageJobStatusResponse`.

**Offen (niedrige Prioritaet):** Externe Clients koennen POST `/generate/image` noch mit `model_key` + Top-Level-Params senden (`ImageGenerateRequest`, `resolve_provider_and_params`, `X-Deprecated`-Header). Entfernen sobald keine Alt-Clients mehr erwartet werden.

---

### Niedrig

#### 32. Provider-Verzeichnis-Inkonsistenz
Image/BgRemoval/Mesh-Provider liegen unter `api/app/services/*_providers/`, Animation/Rigging-Provider
unter `api/app/providers/*/`. Kein einheitliches Muster.

**Empfehlung:** Alle Provider nach `api/app/providers/` konsolidieren (grosser Refactor, niedrige Dringlichkeit).

#### 10. `type: ignore` in main.py
**Weiterhin aktuell:** `api/app/main.py` Zeile ~35 — `# type: ignore[arg-type]` fuer `_rate_limit_exceeded_handler`. Bekannte slowapi-Limitation.

#### 11. Print-Logging in Blender-Skripten
**Weiterhin aktuell:** `api/scripts/blender_rig_human.py` und `api/scripts/blender_bake_textures.py` nutzen `print()` (teilweise `file=sys.stderr`).

**Empfehlung:** Akzeptabel fuer Blender-Subprozesse.

---

## Behebungsplan (offene Punkte)

Ziel: technische Schuld **inkrementell** abbauen — kleine, reviewbare Schritte, keine „alles auf einmal“-Migration.

### Reihenfolge und Abhaengigkeiten

| Phase | Thema | Befund-ID | Abhaengigkeiten |
|-------|--------|-----------|-----------------|
| **1** | `provider_key` / Ende `model_key`-Compat | 4b | Keine harte Abhaengigkeit; vor grossen API-Aenderungen sinnvoll |
| **2** | Texture-Bake-Jobs persistent | 8 | Eigenes DB-Modell + Migration; unabhaengig von Phase 1 |
| **3** | Frontend-Tests ausbauen | 2 | Parallel zu Phase 4/5 moeglich |
| **4** | Coverage-Omits schließen | 7 | Am effizientesten **nach** gezielten Tests pro Modul; koppelt mit Phase 3/5 |
| **5** | Grosse Dateien zerlegen | 6 | Erleichtert Phase 3 und 4 fuer betroffene Bereiche |
| **6** | Niedrig (optional) | 10, 11, 32 | Keine Blocker |

---

### Phase 1: `model_key` bereinigen (4b)

**Stand 2026-03-25:** Punkte 1–2–4–5 fuer **Response/DB/Frontend** erledigt (siehe Befund ~~26~~). Verbleibend: Schritt 3 — `model_key` aus **Request**-Schema und Mapping entfernen, wenn Alt-Clients weg sind.

---

### Phase 2: Texture-Bake-Jobs persistent (8)

**Stand 2026-03-25:** Umgesetzt (Befund ~~25~~). Integrationstest `test_texture_bake_job_persisted_and_status` laeuft mit Postgres (CI); lokal ohne DB `pytest.skip`.

---

### Phase 3: Frontend-Tests (2)

1. **Setup:** Bestehendes Vitest-Setup in `frontend/src/__tests__/` nutzen; React Testing Library fuer Komponenten.
2. **Reihenfolge:** Zuerst **reine Logik** (Hooks, Utils), dann **kritische UI**:
   - `AssetDetailModal` — Speichern, Fehlerpfade (Mocks fuer API).
   - `SketchfabImportModal` — oeffnen/schliessen, Submit-Flow mit Mock.
   - ~~`PipelineStepper`~~ — Basis-Tests in `PipelineStepper.test.tsx`.
   - `JobStatus` / `JobErrorBlock` — Zustaende pending/done/failed.
3. **CI:** Bereits `npm run test` in `.github/workflows/test.yml` — nur Coverage-Qualitaet steigern, kein Pipeline-Change noetig.

**Erfolgskriterium:** Mindestens diese vier Bereiche haben mindestens einen sinnvollen Test; keine Regression bei Refactors in Phase 5.

---

### Phase 4: Coverage-Omits reduzieren (7)

1. **Priorisierung nach Risiko:** Zuerst Router/Services, die Geschaeftslogik tragen (`generation.py`, `assets.py`-Teile, `mesh_generation.py`), dann extern schwer testbare Provider (optional weiter omit oder Contract-Tests).
2. **Vorgehen pro Datei:** Eintrag aus `[tool.coverage.run] omit` in `api/pyproject.toml` entfernen → Tests schreiben bis Coverage wieder >= Schwelle (aktuell `--cov-fail-under=70`).
3. **`__init__.py` und `alembic/*`:** Meist dauerhaft omit-bleibend; nicht zwingend Ziel von Phase 4.
4. **Provider-Globs:** Entweder Integrationstests mit Mocks oder gezielte Unit-Tests pro Provider-Datei; Globs schrittweise verkleinern.

**Erfolgskriterium:** Omits-Liste messbar verkuerzt; keine dauerhafte Coverage-Unterkante unterschritten.

---

### Phase 5: Grosse Dateien zerlegen (6)

1. **Frontend:** `PipelinePage.tsx` — Tabs/Step-Logik in Hooks (`usePipelineSteps`) und Unterkomponenten (`PipelineImageTab`, …); CSS pro Teil auslagern wo sinnvoll.
2. **Frontend:** `AssetLibrary.tsx` — Filter/Grid/Modal in eigene Dateien.
3. **Frontend:** `AssetDetailModal.tsx` — Bereiche (Metadaten, Steps, Export) als Subkomponenten.
4. **Backend:** `generation.py` — Router nach Ressource oder Feature splitten (`generation_image.py`, …) und in `main`/`routers/__init__.py` einbinden.
5. **Backend:** `asset_service.py` — thematische Module (z. B. Metadaten vs. Dateioperationen) mit duennem Fassaden-Import.
6. **Backend:** `assets.py` — Texture-Bake-Routen nach `routers/texture_bake.py` verschieben, sobald Phase 2 stabil ist (optional gekoppelt).

**Erfolgskriterium:** Keine Datei > ca. 500–700 Zeilen ohne triftigen Grund; Reviews werden einfacher.

---

### Phase 6: Niedrig (optional)

- **10 — `type: ignore`:** slowapi-Version pruefen, Stubs suchen, oder duenner Wrapper um den Handler, der mypy befriedigt; nur wenn Aufwand gering.
- **11 — Blender `print()`:** Belassen oder minimale Hilfsfunktion `log_info`/`log_err`, die auf stderr schreibt — keine zwingende Aenderung.
- **32 — Provider-Verzeichnisse:** Alle Provider nach `api/app/providers/` konsolidieren; grosser Refactor, niedrige Dringlichkeit.

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
