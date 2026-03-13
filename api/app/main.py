from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import check_db_connection

app = FastAPI(title="Purzel ML Asset Pipeline API")

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
