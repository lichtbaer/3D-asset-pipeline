import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.storage import (
    ANIMATION_STORAGE_PATH,
    ASSETS_STORAGE_PATH,
    BGREMOVAL_STORAGE_PATH,
    IMAGE_STORAGE_PATH,
    MESH_STORAGE_PATH,
    PRESETS_STORAGE_PATH,
)
from app.database import check_db_connection
from app.logging_config import setup_logging
from app.routers import agents, assets, generation, presets, sketchfab, storage

setup_logging()

MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
PRESETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
BGREMOVAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ANIMATION_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
IMAGE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Purzel ML Asset Pipeline API")
app.include_router(agents.router)
app.include_router(generation.router)
app.include_router(assets.router)
app.include_router(presets.router)
app.include_router(sketchfab.router)
app.include_router(storage.router)
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

_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    db_connected = await check_db_connection()
    return {
        "status": "ok",
        "db": "connected" if db_connected else "disconnected",
    }
