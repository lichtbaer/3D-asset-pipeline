# AGENTS.md – Purzel ML Asset Pipeline

Anleitung für KI-Agenten bei der Arbeit mit diesem Codebase.

**Ausführliche, gepflegte Fassung:** [docs/agents.md](docs/agents.md) (Teil der MkDocs-Site; Vorschau: `pip install -r requirements-docs.txt` und `python3 -m mkdocs serve`).

## Kurzfassung

- **Backend:** Router in `api/app/routers/`, Einbindung in `main.py` unter `/api/v1`; Pydantic v2 / SQLAlchemy 2 async; Alembic für Migrationen.
- **Frontend:** `frontend/src/api/` (Axios, `VITE_API_URL`), `store/` (PipelineStore), Three.js-Viewer.
- **Konfiguration & Storage:** siehe [docs/configuration.md](docs/configuration.md) und [docs/architecture.md](docs/architecture.md).

## Wichtige Hinweise

1. **CORS:** Standard `http://localhost:5173` (über `ALLOWED_ORIGINS` konfigurierbar).
2. **Sprache:** Code und Kommentare sind meist auf Deutsch.
