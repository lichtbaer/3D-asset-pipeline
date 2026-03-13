from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import check_db_connection
from app.routers import generation

from app.config.storage import MESH_STORAGE_PATH

MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Purzel ML Asset Pipeline API")
app.include_router(generation.router)
app.mount("/static/meshes", StaticFiles(directory=str(MESH_STORAGE_PATH)), name="meshes")

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
