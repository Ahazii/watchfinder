"""APScheduler interval for re-processing unmatched listings into the match queue."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import AppSetting

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

KEY_INTERVAL = "match_queue_sync_interval_minutes"


def get_match_queue_sync_interval_minutes(db: Session, settings: Settings) -> int:
    """0 = scheduler job disabled; otherwise minutes between runs (15–1440)."""
    row = db.get(AppSetting, KEY_INTERVAL)
    if row and row.value_text is not None and str(row.value_text).strip() != "":
        try:
            v = int(row.value_text.strip())
            return max(0, min(1440, v))
        except ValueError:
            pass
    return max(0, min(1440, int(settings.match_queue_sync_interval_minutes)))


def set_match_queue_sync_interval_minutes(db: Session, minutes: int) -> None:
    v = max(0, min(1440, int(minutes)))
    row = db.get(AppSetting, KEY_INTERVAL)
    if row:
        row.value_text = str(v)
    else:
        db.add(AppSetting(key=KEY_INTERVAL, value_text=str(v)))
    db.commit()


def sync_match_queue_sync_schedule(
    scheduler: BackgroundScheduler,
    job_func,
    settings: Settings | None = None,
) -> int:
    """Add/reschedule or remove match_queue_sync job. Returns interval minutes or 0 if off."""
    from apscheduler.triggers.interval import IntervalTrigger

    from watchfinder.db import SessionLocal

    settings = settings or get_settings()
    db = SessionLocal()
    try:
        minutes = get_match_queue_sync_interval_minutes(db, settings)
    finally:
        db.close()

    job = scheduler.get_job("match_queue_sync")
    if minutes <= 0:
        if job:
            scheduler.remove_job("match_queue_sync")
        logger.info("Match queue sync scheduler: disabled")
        return 0

    trigger = IntervalTrigger(minutes=minutes)
    if job:
        scheduler.reschedule_job("match_queue_sync", trigger=trigger)
    else:
        scheduler.add_job(
            job_func,
            trigger,
            id="match_queue_sync",
            replace_existing=True,
        )
    logger.info("Match queue sync scheduler: every %s minutes", minutes)
    return minutes
