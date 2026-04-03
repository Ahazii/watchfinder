from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks

from watchfinder.config import get_settings
from watchfinder.db import SessionLocal
from watchfinder.schemas.settings import IngestRunResponse
from watchfinder.services.ingestion.job import run_all_browse_ingest
from watchfinder.services.stale_listing_refresh import run_stale_listing_refresh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _run_ingest_sync() -> None:
    db = SessionLocal()
    try:
        n = run_all_browse_ingest(db)
        logger.info("Manual ingest finished: %s summaries", n)
    except Exception:
        logger.exception("Manual ingest failed")
    finally:
        db.close()


def _run_stale_refresh_sync() -> None:
    db = SessionLocal()
    try:
        stats = run_stale_listing_refresh(db, get_settings())
        logger.info("Manual stale listing refresh: %s", stats)
    except Exception:
        logger.exception("Manual stale listing refresh failed")
    finally:
        db.close()


@router.post("/run", response_model=IngestRunResponse)
def ingest_now(background_tasks: BackgroundTasks) -> IngestRunResponse:
    """Queue a full ingest cycle (all enabled queries). Runs in background."""
    background_tasks.add_task(_run_ingest_sync)
    return IngestRunResponse(
        status="started",
        message="Ingest started in the background. Check container logs for completion.",
    )


@router.post("/stale-refresh-run", response_model=IngestRunResponse)
def stale_refresh_now(background_tasks: BackgroundTasks) -> IngestRunResponse:
    """Queue one stale-listing getItem batch (respects max per run / min age from Settings)."""
    background_tasks.add_task(_run_stale_refresh_sync)
    return IngestRunResponse(
        status="started",
        message="Stale listing refresh started in the background. Check logs for counts.",
    )
