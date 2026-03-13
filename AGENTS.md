# AGENTS.md – Purzel ML Asset Pipeline

Anleitung für KI-Agenten bei der Arbeit mit diesem Codebase.

## Projektüberblick

**Purzel ML Asset Pipeline** – Modularer Experimentierrahmen für KI-gestützte 3D-Asset-Erzeugung. Full-Stack-Anwendung mit FastAPI-Backend, React-Frontend und PostgreSQL.

## Tech Stack

| Schicht   | Technologien |
|-----------|--------------|
| Backend   | Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2 |
| Frontend  | React 19, TypeScript, Vite 8, TanStack Query, Three.js |
| Datenbank | PostgreSQL 16 |
| Infra     | Docker, docker-compose |

## Projektstruktur

```
├── api/                     # FastAPI Backend
│   ├── app/
│   │   ├── main.py          # FastAPI App, CORS für localhost:5173
│   │   ├── database.py      # SQLAlchemy 2.x async
│   │   ├── config/          # Konfiguration (Storage-Pfade, Models)
│   │   ├── models/          # ORM Models
│   │   ├── routers/         # API Router
│   │   ├── schemas/         # Pydantic v2 Schemas
│   │   ├── services/        # Business-Logik
│   │   │   ├── image_providers/   # Bildgenerierung (PicsArt)
│   │   │   ├── mesh_providers/    # Mesh-Generierung (TripoSR, Hunyuan3D, Trellis2)
│   │   │   ├── bgremoval_providers/  # Hintergrundentfernung
│   │   │   └── ...
│   │   ├── providers/       # Animation, Rigging
│   │   └── exceptions.py
│   └── alembic/             # DB-Migrationen
├── frontend/
│   └── src/
│       ├── api/             # API-Client (Axios, VITE_API_URL)
│       ├── components/      # UI-Komponenten
│       ├── pages/           # Seiten
│       └── store/           # State (PipelineStore)
├── storage/                 # Persistente Daten (Volumes)
│   ├── meshes/
│   ├── bgremoval/
│   ├── assets/
│   ├── animations/
│   └── rembg_cache/
└── docker-compose.yml
```

## Entwicklung starten

```bash
# Optional: .env aus .env.example erstellen
cp .env.example .env

# Alle Services starten
docker compose up

# In separatem Terminal: Migrationen ausführen
docker compose exec api alembic upgrade head
```

## Services & URLs

| Service  | URL                     |
|----------|-------------------------|
| API      | http://localhost:8000   |
| Frontend | http://localhost:5173   |
| Health   | http://localhost:8000/health |

## Konventionen für Agenten

### Backend (API)

- **Router:** Neue Endpoints in `api/app/routers/` definieren und in `main.py` einbinden
- **Schemas:** Pydantic v2 in `api/app/schemas/`
- **Models:** SQLAlchemy 2.x in `api/app/models/`
- **Migrationen:** Nach Model-Änderungen `alembic revision --autogenerate` und `alembic upgrade head`
- **Async:** Datenbankzugriffe und externe Calls sind async

### Frontend

- **API-Calls:** Über `frontend/src/api/` (Axios-Instanz mit `VITE_API_URL`)
- **State:** PipelineStore in `frontend/src/store/`
- **Three.js:** MeshViewer, AnimationMeshViewer für 3D-Darstellung

### Umgebungsvariablen

- `PICSART_API_KEY` – PicsArt API (optional)
- `HF_TOKEN` – Hugging Face Token (optional, z.B. für BiRefNet)
- `DATABASE_URL` – PostgreSQL Connection String

### Storage-Pfade

- Meshes: `storage/meshes`
- BgRemoval: `storage/bgremoval`
- Assets: `storage/assets`
- Animations: `storage/animations`
- rembg Cache: `storage/rembg_cache`

### Linting & Tests

- Frontend: `npm run lint` (ESLint)
- Backend: Keine Tests konfiguriert (aktuell)

## Wichtige Hinweise

1. **CORS:** API erlaubt nur `http://localhost:5173` als Origin
2. **Sprache:** Code und Kommentare sind meist auf Deutsch
3. **Branch:** Entwicklung auf `cursor/agents-markdown-file-1020` (Base: `main`)
