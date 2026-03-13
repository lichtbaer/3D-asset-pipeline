from pathlib import Path

from fastapi import FastAPI

from app.logging_config import setup_logging

setup_logging()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import check_db_connection
from app.routers import generation

from app.config.storage import (
    ANIMATION_STORAGE_PATH,
    ASSETS_STORAGE_PATH,
    BGREMOVAL_STORAGE_PATH,
    IMAGE_STORAGE_PATH,
    MESH_STORAGE_PATH,
)
from app.routers import assets

MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
BGREMOVAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ANIMATION_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
IMAGE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Purzel ML Asset Pipeline API")
app.include_router(generation.router)
app.include_router(assets.router)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    db_connected = await check_db_connection()
    return {
        "status": "ok",
        "db": "connected" if db_connected else "disconnected",
    }
