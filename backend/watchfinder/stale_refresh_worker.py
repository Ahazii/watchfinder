from __future__ import annotations

import logging

from watchfinder.config import get_settings
from watchfinder.db import SessionLocal
from watchfinder.services.stale_listing_refresh import (
    get_stale_listing_refresh_enabled,
    run_stale_listing_refresh,
)

logger = logging.getLogger(__name__)


def scheduled_stale_listing_refresh_job() -> None:
    db = SessionLocal()
    try:
        cfg = get_settings()
        if not get_stale_listing_refresh_enabled(db, cfg):
            return
        run_stale_listing_refresh(db, cfg)
    except Exception:
        logger.exception("Scheduled stale listing refresh failed")
    finally:
        db.close()
