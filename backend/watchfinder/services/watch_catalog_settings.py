"""App settings for watch catalog behaviour."""

from __future__ import annotations

from sqlalchemy.orm import Session

from watchfinder.models import AppSetting

KEY_REVIEW_MODE = "watch_catalog_review_mode"
KEY_EXCLUDED_BRANDS = "watch_catalog_excluded_brands"
KEY_QUEUE_REQUIRE_IDENTITY = "watch_catalog_queue_require_identity"
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


def get_watch_catalog_excluded_brands_text(db: Session) -> str:
    """Comma-separated brands saved from Settings UI (may be empty)."""
    row = db.get(AppSetting, KEY_EXCLUDED_BRANDS)
    if not row or row.value_text is None:
        return ""
    return row.value_text


def set_watch_catalog_excluded_brands_text(db: Session, value: str | None) -> None:
    v = (value or "").strip()
    if len(v) > 4000:
        v = v[:4000]
    row = db.get(AppSetting, KEY_EXCLUDED_BRANDS)
    if row:
        row.value_text = v
    else:
        db.add(AppSetting(key=KEY_EXCLUDED_BRANDS, value_text=v))
    db.commit()


def get_watch_catalog_queue_require_identity(db: Session) -> bool:
    """If true, only queue listings with brand + (reference or family)."""
    row = db.get(AppSetting, KEY_QUEUE_REQUIRE_IDENTITY)
    if not row or row.value_text is None:
        return True
    v = row.value_text.strip().lower()
    return v not in {"0", "false", "no", "off"}


def set_watch_catalog_queue_require_identity(db: Session, enabled: bool) -> None:
    row = db.get(AppSetting, KEY_QUEUE_REQUIRE_IDENTITY)
    txt = "true" if bool(enabled) else "false"
    if row:
        row.value_text = txt
    else:
        db.add(AppSetting(key=KEY_QUEUE_REQUIRE_IDENTITY, value_text=txt))
    db.commit()
