from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from watchfinder.api.deps import get_db
from watchfinder.config import get_settings
from watchfinder.schemas.settings import (
    IngestQueryOut,
    SettingsOut,
    SettingsPatch,
)
from watchfinder.services.ingest_schedule import sync_ingest_schedule
from watchfinder.services.ingest_settings import (
    get_ingest_interval_minutes,
    get_ingest_max_pages,
    get_ingest_search_limit,
    list_ingest_queries,
    replace_ingest_queries,
    set_ingest_interval_minutes,
    set_ingest_max_pages,
    set_ingest_search_limit,
)
from watchfinder.services.watch_catalog_settings import (
    get_watch_catalog_review_mode,
    set_watch_catalog_review_mode,
)
from watchfinder import runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_out(db: Session) -> SettingsOut:
    cfg = get_settings()
    rows = list_ingest_queries(db)
    return SettingsOut(
        ingest_interval_minutes=get_ingest_interval_minutes(db, cfg),
        ebay_search_limit=get_ingest_search_limit(db, cfg),
        ingest_max_pages=get_ingest_max_pages(db, cfg),
        ingest_queries=[
            IngestQueryOut(id=r.id, label=r.label, query=r.query, enabled=r.enabled)
            for r in rows
        ],
        env_fallback_query=cfg.ebay_search_query,
        watch_catalog_review_mode=get_watch_catalog_review_mode(db),
    )


@router.get("", response_model=SettingsOut)
def get_settings_api(db: Session = Depends(get_db)) -> SettingsOut:
    return _settings_out(db)


@router.patch("", response_model=SettingsOut)
def patch_settings(body: SettingsPatch, db: Session = Depends(get_db)) -> SettingsOut:
    if body.ingest_interval_minutes is not None:
        set_ingest_interval_minutes(db, body.ingest_interval_minutes)
    if body.ebay_search_limit is not None:
        set_ingest_search_limit(db, body.ebay_search_limit)
    if body.ingest_max_pages is not None:
        set_ingest_max_pages(db, body.ingest_max_pages)
    if body.ingest_queries is not None:
        replace_ingest_queries(
            db,
            [(q.label, q.query, q.enabled) for q in body.ingest_queries],
        )
    if body.watch_catalog_review_mode is not None:
        try:
            set_watch_catalog_review_mode(db, body.watch_catalog_review_mode)
        except ValueError as e:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=str(e)) from e
    sch = runtime.ingest_scheduler
    if sch:
        try:
            from watchfinder.ingest_worker import scheduled_ingest_job

            sync_ingest_schedule(sch, scheduled_ingest_job)
        except Exception:
            logger.exception("Could not reschedule ingest after settings change")
    return _settings_out(db)
