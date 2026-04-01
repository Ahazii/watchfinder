"""Process-wide handles (set from lifespan, used by routes)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

ingest_scheduler: BackgroundScheduler | None = None


def set_ingest_scheduler(scheduler: BackgroundScheduler) -> None:
    global ingest_scheduler
    ingest_scheduler = scheduler
