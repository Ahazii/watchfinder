"""Internal comp bands: recorded sales + fallback active asking prices in DB."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.models import AppSetting, Listing, ParsedAttribute, WatchSaleRecord


def _pctl(sorted_vals: list[Decimal], p: float) -> Decimal | None:
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = min(n - 1, max(0, int(round((n - 1) * p))))
    return sorted_vals[idx]


def _max_comp_limit(db: Session) -> int:
    row = db.get(AppSetting, "max_comp_candidates")
    if row and row.value_text:
        try:
            v = int(row.value_text.strip())
            return max(20, min(2000, v))
        except ValueError:
            pass
    return 200


@dataclass
class CompBand:
    count: int
    p25: Decimal | None
    p75: Decimal | None
    low: Decimal | None
    high: Decimal | None
    label: str


def _sale_prices_for_keys(
    db: Session,
    *,
    exclude_listing_id,
    brand_key: str,
    model_family_key: str | None,
    strict_model: bool,
    limit: int,
) -> list[Decimal]:
    q = select(WatchSaleRecord.sale_price).where(
        WatchSaleRecord.brand_key == brand_key,
        WatchSaleRecord.listing_id != exclude_listing_id,
    )
    if strict_model and model_family_key:
        q = q.where(WatchSaleRecord.model_family_key == model_family_key)
    rows = db.scalars(q.limit(limit * 2)).all()
    vals = sorted(rows)
    return vals[:limit]


def _asking_prices_same_brand(
    db: Session,
    *,
    exclude_listing_id,
    brand_display: str,
    limit: int,
) -> list[Decimal]:
    """Active listings in DB with same parsed brand (case-insensitive)."""
    lids = db.scalars(
        select(ParsedAttribute.listing_id).where(
            ParsedAttribute.namespace == "watch",
            ParsedAttribute.key == "brand",
            ParsedAttribute.value_text.ilike(brand_display.strip()),
        )
    ).all()
    prices: list[Decimal] = []
    seen: set = set()
    for lid in lids:
        if lid == exclude_listing_id or lid in seen:
            continue
        seen.add(lid)
        lst = db.get(Listing, lid)
        if (
            lst
            and lst.is_active
            and lst.current_price is not None
            and lst.current_price > 0
        ):
            prices.append(Decimal(lst.current_price))
        if len(prices) >= limit:
            break
    prices.sort()
    return prices


def compute_comp_bands(
    db: Session,
    *,
    exclude_listing_id,
    brand_display: str | None,
    brand_key: str | None,
    model_family_key: str | None,
    _reference_key: str | None = None,
) -> tuple[CompBand, CompBand]:
    """
    Returns (sales_band, asking_band). Sales may be empty until you record sales.
    """
    limit = _max_comp_limit(db)
    empty = CompBand(0, None, None, None, None, "")

    if not brand_key:
        return (
            empty,
            CompBand(
                0,
                None,
                None,
                None,
                None,
                "No brand — add a brand (parsed or manual) to compute comps.",
            ),
        )

    # Try strict model match first
    sale_vals = _sale_prices_for_keys(
        db,
        exclude_listing_id=exclude_listing_id,
        brand_key=brand_key,
        model_family_key=model_family_key,
        strict_model=True,
        limit=limit,
    )
    if len(sale_vals) < 2:
        sale_vals = _sale_prices_for_keys(
            db,
            exclude_listing_id=exclude_listing_id,
            brand_key=brand_key,
            model_family_key=model_family_key,
            strict_model=False,
            limit=limit,
        )

    sales = CompBand(
        count=len(sale_vals),
        p25=_pctl(sale_vals, 0.25),
        p75=_pctl(sale_vals, 0.75),
        low=sale_vals[0] if sale_vals else None,
        high=sale_vals[-1] if sale_vals else None,
        label="Recorded sales (this database only; excludes this listing).",
    )

    ask_vals: list[Decimal] = []
    if brand_display:
        ask_vals = _asking_prices_same_brand(
            db,
            exclude_listing_id=exclude_listing_id,
            brand_display=brand_display,
            limit=limit,
        )

    asking = CompBand(
        count=len(ask_vals),
        p25=_pctl(ask_vals, 0.25),
        p75=_pctl(ask_vals, 0.75),
        low=ask_vals[0] if ask_vals else None,
        high=ask_vals[-1] if ask_vals else None,
        label="Asking prices — active listings in your database (not sold; p25–p75).",
    )

    return sales, asking
