"""FastAPI aplikace ovladače myčky.

Spuštění (vývoj): ``uv run uvicorn ovladac.main:app``; v kontejneru
``uvicorn ovladac.main:app --host 0.0.0.0``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .routers import api
from .services.appliance import Appliance
from .services.history import History

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Vytvoří správce myčky, spustí čtení stavu na pozadí a při vypnutí ho zruší."""
    settings = Settings()
    appliance = Appliance(settings, History(settings.history_path))
    app.state.appliance = appliance
    task = asyncio.create_task(appliance.run())
    logging.getLogger(__name__).info(
        "myčka %s, čtení á %s s, dry_run=%s", settings.candy_ip, settings.poll_seconds,
        settings.dry_run)
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


STATIC_DIR = Path(__file__).with_name("static")

app = FastAPI(title="Ovladač myčky", lifespan=lifespan)
app.include_router(api.router)
# Až za API: mount na "/" by jinak zachytil i /api/… .
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
