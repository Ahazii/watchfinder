"""App settings for watch catalog behaviour."""

from __future__ import annotations

from sqlalchemy.orm import Session

from watchfinder.models import AppSetting

KEY_REVIEW_MODE = "watch_catalog_review_mode"
VALID_MODES = frozenset({"auto", "review"})


def get_watch_catalog_review_mode(db: Session) -> str:
    """`auto` = match fuzzy + create without queue. `review` = exact match only; else enqueue."""
    row = db.get(AppSetting, KEY_REVIEW_MODE)
    v = (row.value_text or "auto").strip().lower() if row else "auto"
    return v if v in VALID_MODES else "auto"


def set_watch_catalog_review_mode(db: Session, mode: str) -> None:
    m = mode.strip().lower()
    if m not in VALID_MODES:
        raise ValueError("watch_catalog_review_mode must be 'auto' or 'review'")
    row = db.get(AppSetting, KEY_REVIEW_MODE)
    if row:
        row.value_text = m
    else:
        db.add(AppSetting(key=KEY_REVIEW_MODE, value_text=m))
    db.commit()
