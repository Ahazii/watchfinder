"""Refresh Everywatch + Chrono24 snapshot JSON on watch_models; optional fill manual £ bounds."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings
from watchfinder.models import WatchModel
from watchfinder.services.chrono24_client import (
    chrono24_google_site_url,
    chrono24_search_url,
    try_fetch_chrono24_search,
)
from watchfinder.services.everywatch_client import collect_everywatch_snapshot
from watchfinder.services.listing_gbp import gbp_per_unit_of
from watchfinder.services.watch_models import refresh_watch_model_observed_bounds

logger = logging.getLogger(__name__)


def _market_search_query(wm: WatchModel) -> str:
    parts = [wm.brand, wm.reference, wm.model_family]
    return " ".join((p or "").strip() for p in parts if (p or "").strip())


def _parse_iso_dt(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def market_snapshots_need_refresh(
    wm: WatchModel,
    settings: Settings,
) -> bool:
    snap = wm.market_source_snapshots or {}
    ref = _parse_iso_dt(snap.get("last_refresh_at"))
    if ref is None:
        return True
    hours = int(settings.market_snapshot_cooldown_hours)
    return (datetime.now(UTC) - ref.astimezone(UTC)) > timedelta(hours=hours)


def _median_gbp_from_everywatch(
    ew: dict[str, Any],
    settings: Settings,
) -> Decimal | None:
    amt = ew.get("median_amount")
    ccy = ew.get("median_currency")
    if not amt or not ccy:
        return None
    try:
        val = Decimal(str(amt))
    except Exception:
        return None
    rate = gbp_per_unit_of(str(ccy).upper(), settings)
    if rate is None:
        return None
    return (val * rate).quantize(Decimal("0.01"))


def _merge_manual_from_median_gbp(wm: WatchModel, median_gbp: Decimal) -> bool:
    """If manual bounds empty, set a ±10% band around median."""
    if wm.manual_price_low is not None or wm.manual_price_high is not None:
        return False
    low = (median_gbp * Decimal("0.90")).quantize(Decimal("0.01"))
    high = (median_gbp * Decimal("1.10")).quantize(Decimal("0.01"))
    wm.manual_price_low = low
    wm.manual_price_high = high
    return True


def refresh_market_snapshots_for_model(
    db: Session,
    watch_model_id: UUID,
    settings: Settings | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """
    Fetch Everywatch + Chrono24 metadata, merge into **market_source_snapshots**.
    Optionally seeds **manual_price_low/high** when both were null and EW median in GBP works.
    """
    settings = settings or get_settings()
    if not settings.extra_market_import_enabled:
        return {"ok": False, "skipped": "EXTRA_MARKET_IMPORT_ENABLED=false"}

    wm = db.get(WatchModel, watch_model_id)
    if wm is None:
        return {"ok": False, "error": "model not found", "everywatch_hits": 0, "chrono24_hits": 0}

    if not force and not market_snapshots_need_refresh(wm, settings):
        return {"ok": True, "skipped": "cooldown"}

    q = _market_search_query(wm)
    ew = collect_everywatch_snapshot(wm.brand, wm.reference, wm.model_family, settings=settings)
    c24_hits, c24_err = try_fetch_chrono24_search(q, settings=settings)
    now = datetime.now(UTC).isoformat()

    snap: dict[str, Any] = {
        "last_refresh_at": now,
        "search_query": q,
        "everywatch": ew,
        "chrono24": {
            "fetched_at": now,
            "search_url": chrono24_search_url(q, uk=True),
            "google_site_url": chrono24_google_site_url(q),
            "hits": c24_hits[:25],
            "error": c24_err,
        },
    }

    wm.market_source_snapshots = snap
    merged = False
    mg = _median_gbp_from_everywatch(ew, settings)
    if mg is not None:
        merged = _merge_manual_from_median_gbp(wm, mg)

    db.flush()
    refresh_watch_model_observed_bounds(db, wm.id)

    logger.info(
        "market_snapshots model_id=%s ew_hits=%s c24_hits=%s merged_manual=%s",
        watch_model_id,
        len(ew.get("hits") or []),
        len(c24_hits),
        merged,
    )
    return {
        "ok": True,
        "everywatch_hits": len(ew.get("hits") or []),
        "chrono24_hits": len(c24_hits),
        "merged_manual_bounds": merged,
    }


def maybe_refresh_market_snapshots_for_model(
    db: Session,
    watch_model_id: UUID | None,
    settings: Settings | None = None,
) -> None:
    """Called from analyze/backfill; ignores errors."""
    if not watch_model_id:
        return
    try:
        refresh_market_snapshots_for_model(db, watch_model_id, settings=settings, force=False)
    except Exception:
        logger.exception("market_snapshots refresh failed model_id=%s", watch_model_id)
