"""Background job: re-analyze unmatched listings so the match queue stays populated."""

from __future__ import annotations

import logging

from watchfinder.db import SessionLocal
from watchfinder.services.watch_models.catalog import sync_unmatched_listings_watch_catalog

logger = logging.getLogger(__name__)


def scheduled_match_queue_sync_job() -> None:
    db = SessionLocal()
    try:
        stats = sync_unmatched_listings_watch_catalog(db)
        db.commit()
        logger.info("Match queue sync finished: %s", stats)
    except Exception:
        logger.exception("Match queue sync failed")
        db.rollback()
    finally:
        db.close()
