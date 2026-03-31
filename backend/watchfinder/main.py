"""FastAPI entrypoint: health, scheduler-backed ingestion."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from watchfinder.api.routes import candidates, dashboard, listings
from watchfinder.config import get_settings
from watchfinder.db import SessionLocal
from watchfinder.services.ingestion.job import run_browse_ingest

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _ingest_job() -> None:
    db = SessionLocal()
    try:
        run_browse_ingest(db)
    except Exception:
        logger.exception("Scheduled ingest failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    scheduler.add_job(
        _ingest_job,
        "interval",
        minutes=settings.ingest_interval_minutes,
        id="browse_ingest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: Browse ingest every %s minutes",
        settings.ingest_interval_minutes,
    )
    yield
    scheduler.shutdown()


app = FastAPI(title="WatchFinder", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(listings.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Next.js static export (Phase 3): mount last so /api, /health, /docs stay reachable.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_OUT = _REPO_ROOT / "frontend" / "out"
if _FRONTEND_OUT.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_OUT), html=True),
        name="web",
    )
