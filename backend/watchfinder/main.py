"""FastAPI entrypoint: health, scheduler-backed ingestion."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from watchfinder import runtime
from watchfinder.api.routes import (
    candidates,
    dashboard,
    everywatch_debug,
    ingest_admin,
    listings,
    market,
    not_interested,
    watch_link_reviews,
    watch_models,
    watchbase_search,
)
from watchfinder.api.routes import settings as settings_routes
from watchfinder.config import get_settings
from watchfinder.ingest_worker import scheduled_ingest_job
from watchfinder.services.ingest_schedule import sync_ingest_schedule
from watchfinder.services.match_queue_sync_schedule import sync_match_queue_sync_schedule
from watchfinder.services.stale_listing_refresh import sync_stale_listing_refresh_schedule
from watchfinder.match_queue_sync_worker import scheduled_match_queue_sync_job
from watchfinder.stale_refresh_worker import scheduled_stale_listing_refresh_job

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    runtime.set_ingest_scheduler(scheduler)
    minutes = sync_ingest_schedule(scheduler, scheduled_ingest_job, settings)
    stale_every = sync_stale_listing_refresh_schedule(
        scheduler, scheduled_stale_listing_refresh_job, settings
    )
    mq_every = sync_match_queue_sync_schedule(
        scheduler, scheduled_match_queue_sync_job, settings
    )
    scheduler.start()
    logger.info("Scheduler started: Browse ingest every %s minutes", minutes)
    if stale_every:
        logger.info("Stale listing refresh every %s minutes", stale_every)
    else:
        logger.info("Stale listing refresh: off (enable in Settings)")
    if mq_every:
        logger.info("Match queue sync every %s minutes", mq_every)
    else:
        logger.info("Match queue sync: off (set interval in Settings)")
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
app.include_router(not_interested.router, prefix="/api")
app.include_router(watch_models.router, prefix="/api")
app.include_router(watch_link_reviews.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(ingest_admin.router, prefix="/api")
app.include_router(watchbase_search.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(everywatch_debug.router, prefix="/api")

_media_root = Path(get_settings().local_media_root).expanduser().resolve()
_media_root.mkdir(parents=True, exist_ok=True)
app.mount(
    "/api/media",
    StaticFiles(directory=str(_media_root)),
    name="media",
)


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
