"""Scheduled batch refresh of stale active listings via Browse getItem (rate-limited)."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import AppSetting, Listing
from watchfinder.services.ingestion.live_refresh import refresh_listing_from_ebay
from watchfinder.util.app_setting_text import truthy_app_value

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

# Pause between getItem calls to stay polite vs eBay rate limits (not persisted).
_INTER_GET_ITEM_SLEEP_SEC = 0.35

KEY_ENABLED = "stale_listing_refresh_enabled"
KEY_INTERVAL = "stale_listing_refresh_interval_minutes"
KEY_MAX_PER_RUN = "stale_listing_refresh_max_per_run"
KEY_MIN_AGE_HOURS = "stale_listing_refresh_min_age_hours"


def get_stale_listing_refresh_enabled(db: Session, settings: Settings) -> bool:
    row = db.get(AppSetting, KEY_ENABLED)
    if row and row.value_text is not None:
        t = truthy_app_value(row.value_text)
        if t is not None:
            return t
    return bool(settings.stale_listing_refresh_enabled)


def set_stale_listing_refresh_enabled(db: Session, enabled: bool) -> None:
    text = "1" if enabled else "0"
    row = db.get(AppSetting, KEY_ENABLED)
    if row:
        row.value_text = text
    else:
        db.add(AppSetting(key=KEY_ENABLED, value_text=text))
    db.commit()


def get_stale_listing_refresh_interval_minutes(db: Session, settings: Settings) -> int:
    row = db.get(AppSetting, KEY_INTERVAL)
    if row and row.value_text:
        try:
            v = int(row.value_text.strip())
            return max(15, min(1440, v))
        except ValueError:
            pass
    return max(15, min(1440, int(settings.stale_listing_refresh_interval_minutes)))


def set_stale_listing_refresh_interval_minutes(db: Session, minutes: int) -> None:
    v = max(15, min(1440, int(minutes)))
    row = db.get(AppSetting, KEY_INTERVAL)
    if row:
        row.value_text = str(v)
    else:
        db.add(AppSetting(key=KEY_INTERVAL, value_text=str(v)))
    db.commit()


def get_stale_listing_refresh_max_per_run(db: Session, settings: Settings) -> int:
    row = db.get(AppSetting, KEY_MAX_PER_RUN)
    if row and row.value_text:
        try:
            v = int(row.value_text.strip())
            return max(1, min(100, v))
        except ValueError:
            pass
    return max(1, min(100, int(settings.stale_listing_refresh_max_per_run)))


def set_stale_listing_refresh_max_per_run(db: Session, n: int) -> None:
    v = max(1, min(100, int(n)))
    row = db.get(AppSetting, KEY_MAX_PER_RUN)
    if row:
        row.value_text = str(v)
    else:
        db.add(AppSetting(key=KEY_MAX_PER_RUN, value_text=str(v)))
    db.commit()


def get_stale_listing_refresh_min_age_hours(db: Session, settings: Settings) -> int:
    row = db.get(AppSetting, KEY_MIN_AGE_HOURS)
    if row and row.value_text:
        try:
            v = int(row.value_text.strip())
            return max(0, min(720, v))
        except ValueError:
            pass
    return max(0, min(720, int(settings.stale_listing_refresh_min_age_hours)))


def set_stale_listing_refresh_min_age_hours(db: Session, hours: int) -> None:
    v = max(0, min(720, int(hours)))
    row = db.get(AppSetting, KEY_MIN_AGE_HOURS)
    if row:
        row.value_text = str(v)
    else:
        db.add(AppSetting(key=KEY_MIN_AGE_HOURS, value_text=str(v)))
    db.commit()


def iter_stale_active_listing_ids(
    db: Session,
    *,
    min_age_hours: int,
    limit: int,
) -> list[UUID]:
    """Active listings whose last_seen_at is null or older than cutoff, oldest first."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=min_age_hours)
    stmt = (
        select(Listing.id)
        .where(Listing.is_active.is_(True))
        .where(or_(Listing.last_seen_at.is_(None), Listing.last_seen_at < cutoff))
        .order_by(Listing.last_seen_at.asc().nulls_first())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def run_stale_listing_refresh(db: Session, settings: Settings | None = None) -> dict[str, int]:
    """
    Refresh up to max_per_run active listings stale by min_age_hours.
    Returns counts: attempted, updated, ended, errors.
    """
    settings = settings or get_settings()
    max_n = get_stale_listing_refresh_max_per_run(db, settings)
    min_age = get_stale_listing_refresh_min_age_hours(db, settings)
    ids = iter_stale_active_listing_ids(db, min_age_hours=min_age, limit=max_n)
    if not ids:
        n_active = db.scalar(
            select(func.count()).select_from(Listing).where(Listing.is_active.is_(True))
        )
        n_active = int(n_active or 0)
        logger.info(
            "Stale listing refresh: no candidates (min_age_hours=%s, max_per_run=%s). "
            "Active listings in DB: %s — each active row has last_seen_at newer than the cutoff, "
            "or there are no active rows. Lower min age in Settings (0 = eligible if last_seen_at is in the past) or wait.",
            min_age,
            max_n,
            n_active,
        )
    updated = ended = errors = 0
    for i, lid in enumerate(ids):
        if i > 0 and _INTER_GET_ITEM_SLEEP_SEC > 0:
            time.sleep(_INTER_GET_ITEM_SLEEP_SEC)
        try:
            outcome = refresh_listing_from_ebay(db, lid, settings)
            if outcome == "updated":
                updated += 1
            else:
                ended += 1
        except Exception:
            logger.exception("Stale refresh failed listing_id=%s", lid)
            errors += 1
    result = {
        "attempted": len(ids),
        "updated": updated,
        "ended": ended,
        "errors": errors,
    }
    logger.info("Stale listing refresh finished: %s", result)
    return result


def sync_stale_listing_refresh_schedule(
    scheduler: BackgroundScheduler,
    job_func,
    settings: Settings | None = None,
) -> int:
    """Add/reschedule or remove stale_listing_refresh job. Returns interval minutes or 0 if off."""
    from apscheduler.triggers.interval import IntervalTrigger

    from watchfinder.db import SessionLocal

    settings = settings or get_settings()
    db = SessionLocal()
    try:
        enabled = get_stale_listing_refresh_enabled(db, settings)
        minutes = get_stale_listing_refresh_interval_minutes(db, settings)
    finally:
        db.close()

    job = scheduler.get_job("stale_listing_refresh")
    if not enabled:
        if job:
            scheduler.remove_job("stale_listing_refresh")
        logger.info("Stale listing refresh scheduler: disabled")
        return 0

    trigger = IntervalTrigger(minutes=minutes)
    if job:
        scheduler.reschedule_job("stale_listing_refresh", trigger=trigger)
    else:
        scheduler.add_job(
            job_func,
            trigger,
            id="stale_listing_refresh",
            replace_existing=True,
        )
    logger.info("Stale listing refresh scheduler: every %s minutes", minutes)
    return minutes
