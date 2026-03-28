from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config.storage import (
    ANIMATION_STORAGE_PATH,
    ASSETS_STORAGE_PATH,
    BGREMOVAL_STORAGE_PATH,
    IMAGE_STORAGE_PATH,
    MESH_STORAGE_PATH,
    PRESETS_STORAGE_PATH,
)
from app.core.config import settings as app_settings
from app.core.rate_limit import limiter
from app.core.security import verify_api_key
from app.database import check_db_connection
from app.logging_config import setup_logging
from app.routers import agents, assets, generation, presets, providers_health, sketchfab, storage, texture_bake

setup_logging()

MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
PRESETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
BGREMOVAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ANIMATION_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
IMAGE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

_api_auth = [Depends(verify_api_key)]

app = FastAPI(title="Purzel ML Asset Pipeline API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(agents.router)
_v1.include_router(generation.router)
_v1.include_router(assets.router)
_v1.include_router(texture_bake.router)
_v1.include_router(presets.router)
_v1.include_router(sketchfab.router)
_v1.include_router(storage.router)
_v1.include_router(providers_health.router)
app.include_router(_v1, dependencies=_api_auth)
app.mount("/static/meshes", StaticFiles(directory=str(MESH_STORAGE_PATH)), name="meshes")
app.mount(
    "/static/bgremoval",
    StaticFiles(directory=str(BGREMOVAL_STORAGE_PATH)),
    name="bgremoval",
)
app.mount(
    "/static/animations",
    StaticFiles(directory=str(ANIMATION_STORAGE_PATH)),
    name="animations",
)
app.mount(
    "/static/images",
    StaticFiles(directory=str(IMAGE_STORAGE_PATH)),
    name="images",
)

_cors_origins = [o.strip() for o in app_settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


class SecurityHeadersMiddleware:
    """Fügt Security-Headers zu allen Responses hinzu."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
async def health() -> dict[str, str]:
    db_connected = await check_db_connection()
    return {
        "status": "ok",
        "db": "connected" if db_connected else "disconnected",
    }
