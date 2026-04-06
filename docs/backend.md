# Backend

## Einstieg

Die FastAPI-Anwendung wird in `api/app/main.py` erzeugt. Geschäftslogik-Router sind unter dem Prefix **`/api/v1`** gebündelt; Health-Checks und statische Mounts liegen außerhalb dieses Prefixes.

## Router (Überblick)

Router-Module liegen in `api/app/routers/` und werden in `main.py` registriert, u. a.:

| Bereich | Modul (Auszug) |
|---------|----------------|
| Generierung / Jobs | `generation` |
| Assets, Texture-Baking | `assets`, `texture_bake` |
| Presets, Storage, Sketchfab | `presets`, `storage`, `sketchfab` |
| Agenten (Claude) | `agents` |
| Provider-Gesundheit | `providers_health` |

## Services und Provider

- **`app/services/`** — Orchestrierung (Jobs, Fehlerbehandlung), Provider für Bilder, Meshes, Hintergrundentfernung.
- **`app/providers/`** — Animation und Rigging (u. a. UniRig, Blender).

Fehlerbehandlung in Orchestrierungspfaden ist zentral über Hilfsmittel wie `job_error_handler` gelöst (siehe auch [Technical Debt](TECHNICAL_DEBT.md) für historische Änderungen).

## Datenbank

- **ORM:** SQLAlchemy 2.x, async.
- **Migrationen:** Alembic unter `api/alembic/`.

Nach Schemaänderungen im Container:

```bash
docker compose exec api alembic revision --autogenerate -m "kurze_beschreibung"
docker compose exec api alembic upgrade head
```

## Qualitätssicherung (API)

Im Verzeichnis `api/`:

- `pytest` mit Coverage-Ziel
- `mypy app --strict`
- `ruff check app`
- `pip-audit` (Ergebnis-JSON unter `docs/pip-audit-results.json`, gitignored)

Details zum Security-Audit: [Security Audit](SECURITY_AUDIT.md).
