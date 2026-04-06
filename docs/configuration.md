# Konfiguration

## Umgebungsvariablen (Überblick)

Werte kommen aus der Shell-Umgebung, aus `.env` (API nutzt Pydantic Settings) oder aus `docker-compose.yml`.

### API / Laufzeit (`api/app/core/config.py`)

| Variable | Bedeutung |
|----------|-----------|
| `API_KEY` | Optional. Wenn gesetzt: Bearer-Token muss mit diesem Wert übereinstimmen. |
| `ALLOWED_ORIGINS` | Kommagetrennte CORS-Origins (Standard: `http://localhost:5173`). |
| `CORS_ORIGINS` | Optionaler Fallback (siehe `resolved_origins` in Settings). |
| `ANTHROPIC_API_KEY` | Für Agent-Endpoints erforderlich, wenn genutzt. |
| `DATABASE_URL` | PostgreSQL-Connection-String (asyncpg). |
| `LOG_LEVEL` | Log-Level (siehe `logging_config.py`, Standard INFO). |
| `DB_STATEMENT_TIMEOUT_MS` | DB-Statement-Timeout. |
| `IMAGE_DOWNLOAD_TIMEOUT_S` / `MESH_GENERATION_TIMEOUT_S` | Timeouts für externe Schritte. |
| `PROVIDER_MAX_RETRIES` / `PROVIDER_RETRY_BACKOFF_S` | Retry-Verhalten für Provider. |

### Docker Compose (typisch für `api`-Service)

| Variable | Zweck |
|----------|--------|
| `PICSART_API_KEY` | PicsArt (optional) |
| `HF_TOKEN` | Hugging Face (mehrere Provider) |
| `PIAPI_API_KEY` | PiAPI / Trellis u. a. |
| `ANTHROPIC_API_KEY` | Agenten |
| `U2NET_HOME` | rembg-Modellcache (im Compose: `/app/storage/rembg_cache`) |
| `UNIRIG_MODEL_PATH` / `UNIRIG_REPO_PATH` | UniRig lokal — siehe [UniRig lokal](unirig-local.md) |

### Weitere (direkt per `os.getenv` in Modulen)

| Variable | Zweck |
|----------|--------|
| `REPLICATE_API_TOKEN` | Replicate (Provider-Health u. a.) |
| `SKETCHFAB_API_TOKEN` | Sketchfab-Import |
| `BLENDER_EXECUTABLE` | Pfad zu Blender für Rigging/Texture-Baking |

### Frontend

| Variable | Zweck |
|----------|--------|
| `VITE_API_URL` | Basis-URL der API für den Browser |

!!! warning "Keine Secrets in Git"
    `.env` und generierte Audit-JSONs nicht committen. Siehe `.gitignore`.
