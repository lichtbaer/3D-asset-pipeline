"""Entry Point: Poll-Loop für repo_analyzer Tasks."""

import asyncio
import os

import httpx

from analyzer import analyze

ARIA_API_BASE = os.getenv("ARIA_API_BASE", "http://api:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))
HEARTBEAT_INTERVAL = 30
TASK_TYPE = "repo_analyzer"


async def get_next_task() -> dict | None:
    """Holt den nächsten Task von der internen API."""
    if not INTERNAL_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{ARIA_API_BASE}/api/v1/internal/tasks/next",
            params={"type": TASK_TYPE},
            headers={"X-Internal-Api-Key": INTERNAL_API_KEY},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data if data is not None else None


async def heartbeat(task_id: str) -> bool:
    """Sendet Heartbeat für laufenden Task."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            f"{ARIA_API_BASE}/api/v1/internal/tasks/{task_id}/heartbeat",
            headers={"X-Internal-Api-Key": INTERNAL_API_KEY},
        )
        return resp.status_code == 200


async def heartbeat_loop(task_id: str, interval: int = HEARTBEAT_INTERVAL) -> None:
    """Background-Loop: Heartbeat alle interval Sekunden."""
    try:
        while True:
            await asyncio.sleep(interval)
            await heartbeat(task_id)
    except asyncio.CancelledError:
        pass


async def complete_task(task_id: str, result: dict) -> bool:
    """Markiert Task als abgeschlossen."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ARIA_API_BASE}/api/v1/internal/tasks/{task_id}/complete",
            json=result,
            headers={"X-Internal-Api-Key": INTERNAL_API_KEY},
        )
        return resp.status_code == 200


async def fail_task(task_id: str, error: str) -> bool:
    """Markiert Task als fehlgeschlagen."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{ARIA_API_BASE}/api/v1/internal/tasks/{task_id}/fail",
            json={"error": error},
            headers={"X-Internal-Api-Key": INTERNAL_API_KEY},
        )
        return resp.status_code == 200


async def process_task(task: dict) -> None:
    """Verarbeitet einen einzelnen Task."""
    task_id = task.get("id")
    if not task_id:
        return
    await heartbeat(task_id)
    hb_task = asyncio.create_task(heartbeat_loop(task_id, HEARTBEAT_INTERVAL))
    try:
        result = await analyze(task.get("input_payload", {}))
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass
        await complete_task(task_id, result.model_dump())
    except Exception as e:
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass
        await fail_task(task_id, str(e))


async def main() -> None:
    """Poll-Loop: Holt Tasks und verarbeitet sie."""
    while True:
        try:
            task = await get_next_task()
            if task:
                asyncio.create_task(process_task(task))
        except Exception:
            pass
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
