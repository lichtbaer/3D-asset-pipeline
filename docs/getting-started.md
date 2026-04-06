# Erste Schritte

## Voraussetzungen

- Docker und Docker Compose
- Optional: `.env` für API-Keys und lokale Overrides (siehe [Konfiguration](configuration.md))

## Stack starten

```bash
cp .env.example .env   # optional, für Secrets
docker compose up
```

In einem **zweiten Terminal** die Datenbankmigrationen ausführen:

```bash
docker compose exec api alembic upgrade head
```

## URLs

| Dienst | URL | Beschreibung |
|--------|-----|----------------|
| API | http://localhost:8000 | FastAPI |
| Frontend | http://localhost:5173 | React (Vite) |
| Health | http://localhost:8000/health | API-Health-Check |

## Blender (optional, PoC / Tools)

Der Dienst `blender` nutzt das Compose-Profil `tools` und wird für Rigging-Experimente verwendet. Details: [Blender Rigging PoC](BLENDER_RIGGING_POC.md).

```bash
docker compose --profile tools build blender
```

## Nächste Schritte

- [Architektur](architecture.md) — Aufbau der Anwendung
- [Backend](backend.md) — API-Struktur
- [Frontend](frontend.md) — Client und State
