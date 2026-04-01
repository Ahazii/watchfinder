"""Background ingest job (scheduler + manual trigger)."""

from __future__ import annotations

import logging

from watchfinder.db import SessionLocal
from watchfinder.services.ingestion.job import run_all_browse_ingest

logger = logging.getLogger(__name__)


def scheduled_ingest_job() -> None:
    db = SessionLocal()
    try:
        run_all_browse_ingest(db)
    except Exception:
        logger.exception("Scheduled ingest failed")
    finally:
        db.close()
