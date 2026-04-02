# Improvement Proposals — Purzel ML Asset Pipeline

Erstellt: 2026-03-22 (Projektinspektion)

Dieses Dokument fasst alle identifizierten Verbesserungsmaßnahmen zusammen.
Die ersten 5 Einträge wurden als Linear-Issues angelegt (SMA-377–SMA-381).

---

## A — Technical Debt

### [SMA-377] PURZEL-DEBT-001: Frontend-Testabdeckung ⚠ High
Nur 3 Testdateien bei ~100 Komponenten (<5% Abdeckung). Kritische Komponenten
(AssetDetailModal, PipelinePage, JobStatus-Varianten) komplett ungetestet.

**Maßnahme:** Testpyramide mit Vitest + React Testing Library + MSW aufbauen (Infrastruktur bereits vorhanden).
Phase 1: AssetDetailModal, SketchfabImportModal, JobStatus-Varianten.
Phase 2: PipelinePage-Tabs mit MSW-Mocks.
Phase 3: alle Custom Hooks.
**Aufwand:** ~5–8 Tage

---

### PURZEL-DEBT-002: Texture-Baking Job State → DB persistieren ⚠ Normal
`api/app/routers/assets.py` speichert Texture-Baking-Jobs in einem In-Memory-`dict`.
State geht bei Server-Neustart verloren, verhindert horizontales Scaling.

**Maßnahme:** In `GenerationJob`-Tabelle migrieren. Neuer Job-Typ `texture_baking`.
Betroffene Dateien: `assets.py`, `texture_baking_service.py`, neue Alembic-Migration.
**Aufwand:** ~1–2 Tage

---

### PURZEL-DEBT-003: model_key Deprecation → provider_key migrieren ⚠ Normal
`model_key` als deprecated markiert, aber noch in 8 Frontend-Dateien aktiv genutzt.
Backend-Schema hat bereits Backward-Compat-Mapping.

**Maßnahme:** Frontend-Dateien auf `provider_key` migrieren, dann Compat-Mapping und
DB-Feld via Alembic entfernen.
**Aufwand:** ~1 Tag

---

### PURZEL-DEBT-004: Übergroße Komponenten aufteilen ⚠ Normal

| Datei | Zeilen |
|-------|--------|
| `frontend/src/pages/PipelinePage.tsx` | 1369 |
| `frontend/src/pages/AssetLibrary.tsx` | 861 |
| `frontend/src/components/assets/AssetDetailModal.tsx` | 829 |
| `api/app/routers/generation.py` | 1019 |
| `api/app/services/asset_service.py` | 962 |
| `api/app/routers/assets.py` | 798 |

**Maßnahme:** Frontend: Tab-Sections in separate `*TabContent.tsx`-Komponenten extrahieren.
Backend: `generation.py` in je einen Router pro Step aufteilen.
**Aufwand:** ~4–6 Tage (rein strukturell, keine funktionale Änderung)

---

## B — UX-Verbesserungen

### [SMA-379] PURZEL-UX-001: Toast-Notifications ⚠ High
Jobs enden lautlos — kein Feedback für Nutzer. Neues Toast-System mit
`Toast.tsx` + `ToastContext.tsx`. Integration in PipelinePage bei `done`/`failed`.
**Abhängigkeit:** Design System (Farb-Tokens) | **Aufwand:** ~2–3 Tage

---

### [SMA-380] PURZEL-UX-002: Pipeline Stepper ⚠ Normal
6 gleichwertige Tabs ohne sequentielle Workflow-Indikation.
Neue `PipelineStepper.tsx`-Komponente: 5 Steps mit Verbindungslinien, Status
(abgeschlossen/aktiv/gesperrt), `aria-current="step"`.
**Abhängigkeit:** Design System, SVG Icons | **Aufwand:** ~3–4 Tage

---

### [SMA-381] PURZEL-UX-003: Formular-Validierung ⚠ Normal
PromptForm lehnt <10 Zeichen still ab. Neue Komponenten: `CharacterCounter.tsx`,
`InlineError.tsx`, `Tooltip.tsx`. Pattern auf alle 5 Formulare anwenden.
**Abhängigkeit:** Design System (Fehler-Tokens) | **Aufwand:** ~2 Tage

---

### PURZEL-UX-004: Design System Foundations ⚠ Normal
49 inkonsistente `border-radius`-Werte, 8+ Button-Patterns, kein Farb-Token-System
für Error/Success/Warning.

**Maßnahme:**
- `index.css`: Spacing-, Radius-, Shadow-, Farb- und Font-Tokens in `:root`
- `styles/buttons.css`: `.btn`, `.btn--primary`, `.btn--outline`, `.btn--danger`, `.btn--ghost`, `.btn--sm`
- Dupliziertes CSS in `PipelinePage.css` (Z. 76-96 = Z. 141-162) entfernen
- Button-Klassen in 5 TSX-Dateien vereinheitlichen

**Aufwand:** ~2–3 Tage (Grundlage für alle anderen UX-Verbesserungen)

---

### PURZEL-UX-005: Modal-Accessibility ⚠ Normal
`AssetDetailModal` und `AssetPickerModal`: kein Focus-Trap, kein Escape-Handler,
kein `aria-labelledby`, kein Scroll-Lock.

**Maßnahme:** Neue Hooks `useFocusTrap.ts` + `useEscapeKey.ts`. In beide Modals einbauen.
WCAG 2.1 Konformität (2.1.2, 1.3.1).
**Aufwand:** ~1–2 Tage

---

### PURZEL-UX-006: SVG Icons statt Emojis ⚠ Low
Pipeline-Emojis (🖼 ✂️ 🧊 🦴 🎬) sind plattformabhängig.

**Maßnahme:** `components/icons/index.tsx` mit Inline-SVG-Komponenten
(Lucide ISC / Heroicons MIT). Kein npm-Paket, keine externen Abhängigkeiten.
**Aufwand:** ~1–2 Tage

---

### PURZEL-UX-007: Asset Library — Suche, Filter, Lazy-Loading ⚠ Normal
Alle Assets ohne Pagination/Filter. Keine Suchfunktion.

**Maßnahme:**
- Toolbar: Suchfeld, Sort-Dropdown ("Neueste/Älteste"), Filter-Chips je Pipeline-Step
- `useMemo` für client-seitiges Filtern
- `loading="lazy"` auf allen `<img>`-Tags
- Optional: Cursor-basierte Pagination im Backend

**Aufwand:** ~2–3 Tage (Frontend-Filter), +2 Tage (Backend-Pagination)

---

### PURZEL-UX-008: Dark Mode Toggle ⚠ Low
Nur `@media (prefers-color-scheme: dark)` — kein manueller Override.

**Maßnahme:** `useTheme.ts`-Hook mit `localStorage`-Persistenz.
`document.documentElement.dataset.theme` statt Media-Query.
`ThemeToggle.tsx`-Button in Navigation.
**Aufwand:** ~2–3 Tage

---

### PURZEL-UX-009: HomePage Dashboard ⚠ Low
Platzhalter mit Inline-Styles, keine Funktion.

**Maßnahme:** Rewrite mit 4 Sektionen: Quick Actions, Neueste Assets (6 Karten),
Pipeline-Übersicht (Flowchart mit Links), System-Status (Storage, Asset-Zahl).
Neue Komponenten: `RecentAssets.tsx`, `PipelineOverview.tsx`.
**Abhängigkeit:** Design System, SVG Icons, Toast | **Aufwand:** ~3–4 Tage

---

## C — Neue Funktionale Features

### PURZEL-FEAT-001: Pipeline-Automation — Ein-Klick-Durchlauf ⚠ High
[SMA-378] Manueller Step-für-Step-Workflow ist mühsam für Massenproduktion.

**Maßnahme:**
- Backend: `POST /api/v1/pipeline/run` mit `asset_id` + `steps: list[StepConfig]`
- Orchestrierungs-Service mit sequentiellem Step-Execution + Fehler-Tracking
- Frontend: "Auto-Pilot"-Toggle, Step-Konfiguration (Presets je Step), Abbruch-Button
- Fortschritts-SSE oder Polling auf übergeordnetem Job

**Abhängigkeit:** Presets-System vorhanden | **Aufwand:** ~5–7 Tage

---

### PURZEL-FEAT-002: Batch-Generierung — mehrere Varianten parallel ⚠ Normal
Keine Möglichkeit, mehrere Prompt-Varianten gleichzeitig zu generieren.

**Maßnahme:**
- Backend: `POST /api/v1/generation/batch` — startet N parallele Jobs mit Prompt-Variationen
- Frontend: "Varianten"-Dropdown (2/4/8), `BatchJobStatus`-Grid
- Prompt-Agent für automatische Variationen bereits vorhanden

**Aufwand:** ~3–4 Tage

---

### PURZEL-FEAT-003: Provider-Health-Dashboard ⚠ Normal
Keine Sichtbarkeit über Provider-Verfügbarkeit. Fehler erst nach Job-Start sichtbar.

**Maßnahme:**
- Backend: `GET /api/v1/providers/health` — lightweight Ping aller HF-Spaces/APIs, 60s gecacht
- Frontend: Status-Grid in StoragePage oder neue ProvidersPage
- Warnung in Formularen bei offline-Provider

**Aufwand:** ~2–3 Tage

---

### PURZEL-FEAT-004: Asset-Export-Paket — Game-Ready ZIP ⚠ Normal
Assets können nicht als vollständiges Paket heruntergeladen werden.

**Maßnahme:**
- Backend: `GET /api/v1/assets/{id}/export` — Streaming-ZIP mit GLB + Texturen + FBX + metadata.json + preview.png
- Frontend: "Export"-Dropdown in AssetDetailModal (GLB only / FBX+Rig / Vollpaket)

**Aufwand:** ~2–3 Tage

---

### PURZEL-FEAT-005: Cost/Usage-Tracking ⚠ Low
Keine Transparenz über API-Kosten und Token-Verbrauch.

**Maßnahme:**
- `GenerationJob`-Tabelle: neue Felder `cost_usd`, `tokens_used`
- Provider-spezifische Kostenerfassung (Replicate-Response, Anthropic-Tokens bereits tracked)
- Frontend: Kostenanzeige per Job in Step-History, Gesamtkosten-Widget in StoragePage
- `GET /api/v1/stats/costs` für Zeitraum-Aggregation

**Aufwand:** ~3–4 Tage (Token-Counter in Agent-BaseClass bereits vorhanden)

---

### PURZEL-FEAT-006: LOD-Generierung — Low/Mid/High-Poly-Varianten ⚠ Low
Nur ein Mesh ohne Level-of-Detail-Varianten für Game-Engine-Workflows.

**Maßnahme:**
- Backend: `POST /api/v1/assets/{id}/generate-lods` — Open3D Quadric-Decimation für 3 LOD-Stufen
- Speichert `model_lod0/1/2.glb`
- Frontend: "LODs generieren"-Button in Mesh-Processing-Tab

**Keine neuen Dependencies** (Open3D + Trimesh vorhanden) | **Aufwand:** ~2–3 Tage

---

### PURZEL-FEAT-007: Webhook-Integration ⚠ Low
Externe Systeme können nicht automatisch auf Job-Completion reagieren.

**Maßnahme:**
- Neues `WebhookConfig`-Datenmodell mit URL, Events, HMAC-Secret
- `POST/GET/DELETE /api/v1/webhooks`
- Automatischer POST bei Job-Abschluss mit HMAC-SHA256-Signatur + Retry-Logik
- Frontend: Webhook-Management in StoragePage

**Aufwand:** ~3–4 Tage

---

## D — Neue Funktionale Features (2026-04-01)

### PURZEL-FEAT-008: Image-to-Image Generation ⚠ Normal
Nutzer können nur per Textprompt starten. Für iterative Verfeinerung oder Style-Transfer
ist img2img nötig — Replicate (FLUX Dev, SDXL) und HF Inference unterstützen es nativ.

**Maßnahme:**
- `ImageGenerateRequest`: optionales Feld `reference_image_url: str | None`
- `ReplicateImageProvider`: bei gesetztem `reference_image_url` → `input_params["image"]` befüllen
- `HFInferenceProvider`: `client.image_to_image()` statt `text_to_image()`
- `ImageProvider`-Basisklasse: Signatur um `reference_image_url` erweitern
- Frontend `PromptForm`: Drag-Drop-Zone für Referenzbild, neuer `img2img_strength`-Slider (0.0–1.0)

**Betroffene Dateien:** `api/app/schemas/generation.py`, `api/app/services/image_providers/base.py`,
`replicate_provider.py`, `hf_inference.py`, `frontend/src/components/generation/PromptForm.tsx`
**Aufwand:** ~3–4 Tage

---

### PURZEL-FEAT-009: Auto Quality Gate nach Mesh-Generierung ⚠ Normal
`QualityAgent` existiert, wird aber nur manuell aufgerufen. Meshes mit High-Severity-Issues
(fehlende Gliedmaßen, Floor-Artefakte) fließen still in den Rigging-Step, der dann
kryptisch fehlschlägt.

**Maßnahme:**
- Nach erfolgreicher Mesh-Generierung in `generation_mesh.py`: automatisch `quality_agent.run()`
  mit Vorschau-URL + Mesh-Kennzahlen aufrufen
- `QualityAssessment` in Asset-Metadaten persistieren: `quality_score`, `rigging_suitable`,
  `quality_issues` (JSON) via `metadata_service.py`
- Frontend: farbiger Badge in `AssetGrid`-Karte (rot/gelb/grün) + Detail in `AssetDetailModal`
- Konfigurierbar: `auto_quality_check: bool` in `MeshGenerateRequest`; bei `rigging_suitable=false`
  → Warnung im Rigging-Tab (kein Hard-Block, Nutzer kann übersteuern)

**Keine neuen Dependencies** (QualityAgent bereits vorhanden)
**Aufwand:** ~2–3 Tage

---

### PURZEL-FEAT-010: Globale Job-Queue-Ansicht ⚠ Normal
Alle Jobs sind nur per-Asset sichtbar. Kein Überblick über laufende / fehlgeschlagene Jobs
quer über alle Assets — besonders schmerzhaft bei Pipeline-Automation (FEAT-001).

**Maßnahme:**
- Neuer Endpoint `GET /api/v1/jobs` in `generation_jobs.py`:
  Filter-Parameter `status`, `job_type`, `since` (ISO-Datetime), `limit`, `offset`
- Paginierte Response mit `job_id`, `asset_id`, `job_type`, `status`, `provider_key`,
  `created_at`, `error_detail`
- Frontend: `JobQueuePanel`-Komponente in `StoragePage.tsx`
  - Tabelle mit Status-Badge, Asset-Link, Provider, Zeitstempel, Fehlertext
  - Filter-Chips: All / Running / Failed / Done
  - Auto-Refresh alle 10 s

**Aufwand:** ~2–3 Tage

---

### PURZEL-FEAT-011: Retry mit Original-Parametern ⚠ Normal
Bei Job-Fehler müssen alle Parameter (Prompt, Provider, Dimensionen) manuell neu eingegeben
werden. `GenerationJob` speichert bereits alle relevanten Felder — die Information liegt vor,
wird aber nicht genutzt.

**Maßnahme:**
- Neuer Endpoint `POST /api/v1/jobs/{job_id}/retry` in `generation_jobs.py`:
  liest Original-Job aus DB, erstellt neuen Job desselben `job_type` mit identischen Parametern
  (Original bleibt erhalten → Verlauf vollständig)
- Frontend: „Erneut versuchen"-Button in `JobErrorBlock.tsx`
  Klick → neue `job_id` → SSE-Subscription wie normaler Job-Start
- Optional: „Retry mit angepassten Parametern" öffnet Formular vorausgefüllt

**Aufwand:** ~1–2 Tage

---

### PURZEL-FEAT-012: Prompt-Verlauf & Favoriten ⚠ Low
Nutzer wiederholen ähnliche Prompts, tippen sie aber jedes Mal neu.
Prompt-Agent-Varianten gehen nach Page-Reload verloren.

**Maßnahme:**
- Neue DB-Tabelle `prompt_history`:
  `id`, `prompt_text`, `enhanced_prompt` (nullable), `provider_key`, `used_count`,
  `is_favorite`, `created_at`
- Alembic-Migration
- Endpoints: `GET /api/v1/prompts/history`, `POST` (auto bei Job-Start),
  `PATCH /{id}/favorite`, `DELETE /{id}`
- Frontend: Dropdown-Overlay unter Prompt-Textarea in `PromptForm.tsx`
  „Zuletzt verwendet" + Favoriten-Stern; Klick → Prompt übernehmen

**Aufwand:** ~2–3 Tage

---

### PURZEL-FEAT-013: Blender Vorschau-Render ⚠ Low
Asset-Thumbnails basieren auf Three.js-Canvas-Screenshots (auflösungsbegrenzt,
GPU-abhängig, nur interaktiv). Für Batch-Workflows fehlen automatisch generierte
Vorschaubilder vollständig.

**Maßnahme:**
- Neues Blender-Skript `api/scripts/blender_render_preview.py`:
  GLB laden, HDRI-Beleuchtung setzen, 512×512 PNG mit EEVEE (~5 s) oder Cycles (~30 s)
  rendern, unter `storage/assets/{asset_id}/preview.png` speichern
- Neuer Endpoint `POST /api/v1/assets/{id}/render-preview` → startet Blender-Subprocess
  (analog zu `texture_bake.py`-Muster)
- Auto-Trigger: optionales Flag nach erfolgreicher Mesh-Generierung
- Frontend: `preview.png` in `AssetGrid`-Karte statt dynamischem Three.js-Canvas

**Abhängigkeit:** Blender-Docker-Profil (`--profile tools`) | **Aufwand:** ~3–4 Tage

---

---

## E — Neue Funktionale Features (2026-04-02) ✅ Implementiert

### FEAT-NEW-001: Auto-Tagging nach Mesh-Generierung ✅
Der `tagging_agent` wird nach jedem erfolgreichen Mesh-Job automatisch ausgelöst.
Generierte Tags werden direkt in `metadata.json` persistiert. Überspringt
stillschweigend wenn `ANTHROPIC_API_KEY` nicht gesetzt oder Tags bereits vorhanden.

**Implementiert in:**
- `api/app/services/auto_tag_service.py` (neu)
- `api/app/services/job_service.py` (Hook nach `persist_mesh_job`)

---

### FEAT-NEW-002: Animation Playback im Asset-Detail-Viewer ✅
`AnimationMeshViewer` (vorhandene Komponente) wird jetzt im `AssetDetailModal`
für den Animation-Step angezeigt. Play/Pause/Scrubber/Clip-Auswahl verfügbar.

**Implementiert in:**
- `frontend/src/components/assets/AssetFilesPreviews.tsx`

---

### FEAT-NEW-003: 3D-Print Readiness Check ✅
Neuer Endpoint `GET /assets/{id}/print-readiness` prüft Watertightness, Manifold,
Self-Intersections und gibt Bounding-Box in mm zurück. "Druckeignung prüfen"-Button
im Export-Panel zeigt Checkliste und Dimensionen.

**Implementiert in:**
- `api/app/services/mesh_processing_service.py` (`print_readiness()`)
- `api/app/schemas/asset.py` (`PrintReadinessReport`, `PrintReadinessCheck`, `PrintReadinessStats`)
- `api/app/routers/assets.py` (`GET /assets/{id}/print-readiness`)
- `frontend/src/api/assets.ts` (`checkPrintReadiness()`)
- `frontend/src/components/assets/ExportPanel.tsx`

---

### FEAT-NEW-004: Asset Duplizierung ✅
`POST /assets/{id}/duplicate` klont Asset-Ordner mit frischer UUID. Name, Tags,
Notes, Rating werden übernommen. Optional `?up_to_step=mesh` für partielle Kopie.
"⎘ Duplizieren"-Button im Modal-Header.

**Implementiert in:**
- `api/app/services/asset_service.py` (`duplicate_asset()`)
- `api/app/schemas/asset.py` (`DuplicateAssetResponse`)
- `api/app/routers/assets.py` (`POST /assets/{id}/duplicate`)
- `frontend/src/api/assets.ts` (`duplicateAsset()`)
- `frontend/src/components/assets/AssetDetailModal.tsx`

---

### FEAT-NEW-005: Auto-Repair nach Quality Assessment ✅
`POST /assets/{id}/auto-repair` führt geordnete Repair-Aktionen aus dem
Quality-Agent automatisch aus (`clip_floor`, `repair_mesh`, `simplify`,
`remove_components`). "⚙ Auto-Repair ausführen"-Button in `QualityAnalysisPanel`,
sichtbar wenn reparierbare Aktionen empfohlen wurden.

**Implementiert in:**
- `api/app/services/mesh_processing_service.py` (`auto_repair()`)
- `api/app/schemas/asset.py` (`AutoRepairResponse`)
- `api/app/routers/assets.py` (`POST /assets/{id}/auto-repair`)
- `frontend/src/api/assets.ts` (`autoRepairMesh()`)
- `frontend/src/components/assets/QualityAnalysisPanel.tsx`

---

### FEAT-NEW-006: Mesh-Metriken-Vergleich ✅
Neue `MeshStatsTable`-Komponente zeigt detaillierte Kennzahlen (Vertices, Faces,
Watertight, Manifold, Duplikate, Dateigröße, Bounding-Box-Dimensionen). Wenn mehrere
Mesh-Varianten vorhanden: `MeshComparePanel` mit Delta-Tabelle (Faces ±, Vertices ±,
Dateigröße). Neuer Endpoint `GET /assets/{id}/mesh-stats`.

**Implementiert in:**
- `api/app/schemas/asset.py` (`MeshStatsResponse`)
- `api/app/routers/assets.py` (`GET /assets/{id}/mesh-stats`)
- `frontend/src/api/assets.ts` (`getMeshStats()`)
- `frontend/src/components/assets/MeshProcessingPanel.tsx` (`MeshStatsTable`, `MeshComparePanel`)

---

## Prioritäts-Übersicht

| # | Issue | Typ | Prio | Aufwand |
|---|-------|-----|------|---------|
| SMA-377 | Frontend-Testabdeckung | Debt | High | 5–8 Tage |
| SMA-378 | Pipeline-Automation | Feature | High | 5–7 Tage |
| SMA-379 | Toast-Notifications | UX | High | 2–3 Tage |
| SMA-380 | Pipeline Stepper | UX | Normal | 3–4 Tage |
| SMA-381 | Formular-Validierung | UX | Normal | 2 Tage |
| — | Design System Foundations | UX | Normal | 2–3 Tage |
| — | Modal-Accessibility | UX | Normal | 1–2 Tage |
| — | Asset Library Filter/Suche | UX | Normal | 2–3 Tage |
| — | Texture-Baking → DB | Debt | Normal | 1–2 Tage |
| — | model_key Deprecation | Debt | Normal | 1 Tag |
| — | Übergroße Komponenten | Debt | Normal | 4–6 Tage |
| — | Batch-Generierung | Feature | Normal | 3–4 Tage |
| — | Provider-Health-Dashboard | Feature | Normal | 2–3 Tage |
| — | Asset-Export-Paket | Feature | Normal | 2–3 Tage |
| — | Image-to-Image Generation | Feature | Normal | 3–4 Tage |
| — | Auto Quality Gate | Feature | Normal | 2–3 Tage |
| — | Globale Job-Queue-Ansicht | Feature | Normal | 2–3 Tage |
| — | Retry mit Original-Parametern | Feature | Normal | 1–2 Tage |
| — | SVG Icons | UX | Low | 1–2 Tage |
| — | Dark Mode Toggle | UX | Low | 2–3 Tage |
| — | HomePage Dashboard | UX | Low | 3–4 Tage |
| — | Cost/Usage-Tracking | Feature | Low | 3–4 Tage |
| — | LOD-Generierung | Feature | Low | 2–3 Tage |
| — | Webhook-Integration | Feature | Low | 3–4 Tage |
| — | Prompt-Verlauf & Favoriten | Feature | Low | 2–3 Tage |
| — | Blender Vorschau-Render | Feature | Low | 3–4 Tage |
| ✅ | Auto-Tagging nach Mesh-Generierung | Feature | Normal | 0,5 Tage |
| ✅ | Animation Playback im Asset-Detail-Viewer | Feature | Normal | 0,5 Tage |
| ✅ | 3D-Print Readiness Check | Feature | Low | 1 Tag |
| ✅ | Asset Duplizierung | Feature | Normal | 1 Tag |
| ✅ | Auto-Repair nach Quality Assessment | Feature | Normal | 1 Tag |
| ✅ | Mesh-Metriken-Vergleich | Feature | Low | 1 Tag |

**Gesamtaufwand geschätzt (ursprünglich):** ~68–99 Entwicklungstage
**Implementiert 2026-04-02:** 6 neue Features (~5 Entwicklungstage)
