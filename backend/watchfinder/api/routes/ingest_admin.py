from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks

from watchfinder.config import get_settings
from watchfinder.db import SessionLocal
from watchfinder.schemas.settings import ActiveRefreshStatusResponse, IngestRunResponse
from watchfinder.services.ingestion.job import run_all_browse_ingest
from watchfinder.services.stale_listing_refresh import (
    run_full_active_listing_refresh,
    run_stale_listing_refresh,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])
_active_refresh_lock = threading.Lock()
_active_refresh_status: dict[str, object] = {
    "running": False,
    "total": 0,
    "processed": 0,
    "updated": 0,
    "ended": 0,
    "errors": 0,
    "current_item_id": None,
    "current_index": 0,
    "last_status": None,
    "last_error": None,
    "started_at": None,
    "finished_at": None,
}


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


def _set_active_refresh_status(patch: dict[str, object]) -> None:
    with _active_refresh_lock:
        _active_refresh_status.update(patch)


def _run_full_active_refresh_sync() -> None:
    db = SessionLocal()
    try:
        _set_active_refresh_status(
            {
                "running": True,
                "total": 0,
                "processed": 0,
                "updated": 0,
                "ended": 0,
                "errors": 0,
                "current_item_id": None,
                "current_index": 0,
                "last_status": "Starting",
                "last_error": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
            }
        )
        stats = run_full_active_listing_refresh(
            db, settings=get_settings(), progress_cb=_set_active_refresh_status
        )
        _set_active_refresh_status(
            {
                "running": False,
                "last_status": "Finished",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "total": int(stats.get("attempted", 0)),
                "updated": int(stats.get("updated", 0)),
                "ended": int(stats.get("ended", 0)),
                "errors": int(stats.get("errors", 0)),
                "processed": int(stats.get("attempted", 0)),
                "current_index": int(stats.get("attempted", 0)),
            }
        )
    except Exception as exc:
        logger.exception("Manual full active refresh failed")
        _set_active_refresh_status(
            {
                "running": False,
                "last_status": "Failed",
                "last_error": str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
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


@router.post("/active-refresh-all-run", response_model=IngestRunResponse)
def active_refresh_all_now(background_tasks: BackgroundTasks) -> IngestRunResponse:
    with _active_refresh_lock:
        if bool(_active_refresh_status.get("running")):
            return IngestRunResponse(
                status="already_running",
                message="Full active refresh is already running.",
            )
    background_tasks.add_task(_run_full_active_refresh_sync)
    return IngestRunResponse(
        status="started",
        message="Full active refresh started. Watch progress below.",
    )


@router.get("/active-refresh-all-status", response_model=ActiveRefreshStatusResponse)
def active_refresh_all_status() -> ActiveRefreshStatusResponse:
    with _active_refresh_lock:
        snap = dict(_active_refresh_status)
    return ActiveRefreshStatusResponse(**snap)
