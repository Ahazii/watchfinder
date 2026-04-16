"""Donor movement asking-price bands from movement_only listings linked to a caliber."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.models import Caliber, Listing, ListingCaliber, WatchModel
from watchfinder.numeric_stats import percentile_sorted
from watchfinder.services.entities.normalize import normalize_entity_key
from watchfinder.services.listing_status import active_listing_clause

_CAL_FUZZ = 82


def find_caliber_by_text(db: Session, raw: str | None) -> Caliber | None:
    """Match catalog caliber row by normalized key or fuzzy display_text (read-only, no create)."""
    from rapidfuzz import fuzz, process

    if not raw or not str(raw).strip():
        return None
    s = raw.strip()
    nk = normalize_entity_key(s)
    if not nk:
        return None
    row = db.scalar(select(Caliber).where(Caliber.norm_key == nk))
    if row:
        return row
    all_c = db.scalars(select(Caliber)).all()
    if not all_c:
        return None
    hit = process.extractOne(
        s, [c.display_text for c in all_c], scorer=fuzz.WRatio, score_cutoff=_CAL_FUZZ
    )
    if hit:
        _, score, idx = hit
        if score >= _CAL_FUZZ:
            return all_c[idx]
    return None


def donor_movement_price_bands_for_caliber(
    db: Session,
    caliber_id: UUID,
    *,
    currency: str | None = None,
) -> tuple[list[dict], int]:
    """
    Active movement_only listings with this caliber_id and a price, grouped by currency.

    Returns (bands, total_row_count) where each band has
    currency, sample_count, p25, median, p75, low, high (Decimals or None).
    """
    stmt = (
        select(Listing.currency, Listing.current_price)
        .join(ListingCaliber, ListingCaliber.listing_id == Listing.id)
        .where(
            ListingCaliber.caliber_id == caliber_id,
            Listing.listing_type == "movement_only",
            Listing.current_price.isnot(None),
            active_listing_clause(),
        )
    )
    if currency and currency.strip():
        c = currency.strip().upper()
        stmt = stmt.where(Listing.currency == c)

    rows = db.execute(stmt).all()
    by_ccy: dict[str, list[Decimal]] = defaultdict(list)
    for cur, price in rows:
        if price is None:
            continue
        key = (cur or "").strip().upper() or "?"
        by_ccy[key].append(price)

    bands: list[dict] = []
    total = 0
    for ccy, vals in sorted(by_ccy.items(), key=lambda x: x[0]):
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        total += n
        bands.append(
            {
                "currency": ccy,
                "sample_count": n,
                "p25": percentile_sorted(vals_sorted, 0.25),
                "median": percentile_sorted(vals_sorted, 0.50),
                "p75": percentile_sorted(vals_sorted, 0.75),
                "low": vals_sorted[0],
                "high": vals_sorted[-1],
            }
        )
    return bands, total


def build_donor_market_payload(
    db: Session,
    *,
    caliber: Caliber,
    currency: str | None = None,
    match_note: str | None = None,
) -> dict:
    bands, total = donor_movement_price_bands_for_caliber(db, caliber.id, currency=currency)
    return {
        "caliber_id": caliber.id,
        "caliber_display_text": caliber.display_text,
        "caliber_norm_key": caliber.norm_key,
        "listing_type": "movement_only",
        "total_samples": total,
        "bands": bands,
        "match_note": match_note,
    }


def donor_market_for_watch_model(
    db: Session, wm: WatchModel, *, currency: str | None = None
) -> dict | None:
    """Resolve caliber from watch_models.caliber and return donor market stats, or None if unresolved."""
    cal = find_caliber_by_text(db, wm.caliber)
    if not cal:
        return {
            "caliber_id": None,
            "caliber_display_text": None,
            "caliber_norm_key": None,
            "listing_type": "movement_only",
            "total_samples": 0,
            "bands": [],
            "match_note": (
                "No caliber dictionary row matched this model’s caliber text. "
                "Edit the caliber field or run entity backfill so listings link calibers."
                if (wm.caliber and str(wm.caliber).strip())
                else "No caliber set on this catalog row."
            ),
        }
    match_note = f"Matched dictionary caliber from model text: {wm.caliber!r} → {cal.display_text!r}"
    return build_donor_market_payload(db, caliber=cal, currency=currency, match_note=match_note)
