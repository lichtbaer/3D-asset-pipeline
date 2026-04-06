# Purzel ML Asset Pipeline

Modularer Experimentierrahmen für KI-gestützte 3D Asset-Erzeugung.

**Vollständige Dokumentation (MkDocs):** `pip install -r requirements-docs.txt`, dann `python3 -m mkdocs serve` (Standard: http://127.0.0.1:8001). Die Quellen liegen in [`docs/`](docs/).

## Quick Start

```bash
# Optional: .env aus .env.example erstellen (für Secrets)
cp .env.example .env

# Alle Services starten
docker compose up

# In separatem Terminal: Datenbank-Migrationen ausführen
docker compose exec api alembic upgrade head
```

## Services

| Service   | URL                    | Beschreibung        |
|-----------|------------------------|---------------------|
| API       | http://localhost:8000  | FastAPI Backend     |
| Frontend  | http://localhost:5173  | React/Vite App      |
| Health    | http://localhost:8000/health | API Health-Check |

## Projektstruktur

```
├── api/                 # FastAPI Backend
│   ├── app/
│   │   ├── main.py      # FastAPI App, CORS für localhost:5173
│   │   ├── database.py  # SQLAlchemy 2.x async
│   │   ├── models/      # ORM Models
│   │   ├── routers/     # API Router (bereit für PURZEL-002)
│   │   └── schemas/     # Pydantic v2 Schemas
│   └── alembic/         # Migrations
├── frontend/            # React + Vite
│   └── src/
│       ├── api/         # Axios-Instanz (VITE_API_URL)
│       ├── components/  # UI-Komponenten
│       └── pages/       # Seiten
└── docker-compose.yml   # api, frontend, db (PostgreSQL 16)
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic v2
- **Frontend:** React, TypeScript, Vite, Axios
- **DB:** PostgreSQL 16
- **Dev:** Docker, docker-compose

## UniRig Lokal

Für lokales Rigging ohne Hugging Face Space (keine externe Abhängigkeit, geringere Latenz):

**Voraussetzungen:** CUDA-fähige GPU (>8 GB VRAM), PyTorch mit CUDA, UniRig-Repo, Blender (bpy)

1. **Checkpoint herunterladen** (einmalig, ~5 GB):

   ```bash
   huggingface-cli download VAST-AI/UniRig --local-dir ./models/unirig/
   ```

2. **UniRig-Repo klonen** (für Inferenz-Skripte):

   ```bash
   git clone https://github.com/VAST-AI-Research/UniRig ./unirig/
   cd unirig && pip install -r requirements.txt
   ```

3. **Umgebungsvariablen** in `.env`:

   ```
   UNIRIG_MODEL_PATH=./models/unirig/
   UNIRIG_REPO_PATH=./unirig/
   ```

4. **Docker mit GPU:** In `docker-compose.yml` den GPU-Block für den API-Service aktivieren (siehe Kommentar).

Ohne CUDA oder fehlendem Checkpoint wird der Provider `unirig-local` nicht registriert; der Server startet trotzdem.

Details zu UniRig und weiteren Themen: siehe die [MkDocs-Dokumentation](docs/index.md) bzw. `python3 -m mkdocs serve`.
