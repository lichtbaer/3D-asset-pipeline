# Purzel ML Asset Pipeline

Modularer Experimentierrahmen für KI-gestützte 3D Asset-Erzeugung.

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
