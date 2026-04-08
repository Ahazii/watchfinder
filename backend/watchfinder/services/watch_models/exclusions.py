"""Catalog brand exclusions (env WATCH_CATALOG_EXCLUDED_BRANDS + Settings UI app_settings)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import AppSetting
from watchfinder.services.watch_catalog_settings import KEY_EXCLUDED_BRANDS


def parse_excluded_brand_names(raw: str | None) -> frozenset[str]:
    if not raw or not str(raw).strip():
        return frozenset()
    out: list[str] = []
    for part in str(raw).split(","):
        t = part.strip().lower()
        if t:
            out.append(t)
    return frozenset(out)


def catalog_excluded_brands(db: Session, settings: Settings | None = None) -> frozenset[str]:
    """
    Union of env-based names and persisted Settings UI list (both apply).
    """
    settings = settings or get_settings()
    from_env = parse_excluded_brand_names(settings.watch_catalog_excluded_brands)
    row = db.get(AppSetting, KEY_EXCLUDED_BRANDS)
    from_db = parse_excluded_brand_names(row.value_text if row else None)
    return frozenset(from_env | from_db)


def brand_is_catalog_excluded(brand: str | None, excluded: frozenset[str]) -> bool:
    if not brand or not excluded:
        return False
    return brand.strip().lower() in excluded
