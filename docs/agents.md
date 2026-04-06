# Konventionen für Agenten und Entwickler:innen

Anleitung für Arbeit am Codebase (KI-Agenten und Menschen).

## Projektüberblick

**Purzel ML Asset Pipeline** — Experimentierrahmen für KI-gestützte 3D-Asset-Erzeugung: FastAPI, React, PostgreSQL. Ausführlicher Überblick: [Architektur](architecture.md) und [Startseite](index.md).

## Backend (API)

- **Router:** Neue Endpunkte in `api/app/routers/`, in `main.py` unter `/api/v1` einbinden.
- **Schemas:** Pydantic v2 in `api/app/schemas/`.
- **Models:** SQLAlchemy 2.x in `api/app/models/`.
- **Migrationen:** Nach Modeländerungen `alembic revision --autogenerate` und `alembic upgrade head`.
- **Async:** DB und externe Aufrufe sind async.

## Frontend

- **API-Calls:** `frontend/src/api/` (Axios, `VITE_API_URL`).
- **State:** `PipelineStore` in `frontend/src/store/`.
- **Three.js:** MeshViewer, AnimationMeshViewer.

## Umgebungsvariablen (Kurz)

Siehe die vollständige Tabelle unter [Konfiguration](configuration.md). Häufig:

- `PICSART_API_KEY`, `HF_TOKEN`, `PIAPI_API_KEY`, `DATABASE_URL`, `API_KEY`, `ANTHROPIC_API_KEY`

## Storage-Pfade

- Meshes: `storage/meshes`
- BgRemoval: `storage/bgremoval`
- Assets: `storage/assets`
- Animations: `storage/animations`
- rembg-Cache: `storage/rembg_cache`

## Linting und Tests

- Frontend: `npm run lint` (ESLint), `npm run test` (Vitest)
- Backend: siehe CI — pytest, mypy, ruff, pip-audit

## Hinweise

1. **CORS:** Standard-Origin der API ist `http://localhost:5173` (über `ALLOWED_ORIGINS` anpassbar).
2. **Sprache:** Code und Kommentare sind überwiegend Deutsch.
3. **Dokumentation:** Diese Seite ist Teil der MkDocs-Site; Root-Datei `AGENTS.md` verweist hierher.
