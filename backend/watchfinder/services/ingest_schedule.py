"""APScheduler interval sync from DB + env fallback."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from watchfinder.config import Settings, get_settings
from watchfinder.db import SessionLocal
from watchfinder.services.ingest_settings import get_ingest_interval_minutes

logger = logging.getLogger(__name__)


def sync_ingest_schedule(
    scheduler: BackgroundScheduler,
    job_func,
    settings: Settings | None = None,
) -> int:
    """Reschedule or add browse_ingest job. Returns effective interval minutes."""
    settings = settings or get_settings()
    db = SessionLocal()
    try:
        minutes = get_ingest_interval_minutes(db, settings)
    finally:
        db.close()
    trigger = IntervalTrigger(minutes=minutes)
    job = scheduler.get_job("browse_ingest")
    if job:
        scheduler.reschedule_job("browse_ingest", trigger=trigger)
    else:
        scheduler.add_job(
            job_func,
            trigger,
            id="browse_ingest",
            replace_existing=True,
        )
    logger.info("Ingest schedule: every %s minutes", minutes)
    return minutes
