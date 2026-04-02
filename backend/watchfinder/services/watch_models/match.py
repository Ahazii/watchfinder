"""Auto-link listings to watch_models; refresh observed price bounds from listings + sale records."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from watchfinder.models import Listing, ListingEdit, WatchModel, WatchSaleRecord
from watchfinder.services.valuation.effective import (
    effective_model_family,
    effective_reference,
    norm_key,
)

if TYPE_CHECKING:
    pass


def _find_by_brand_ref(db: Session, brand_display: str, ref: str) -> WatchModel | None:
    bk, rk = norm_key(brand_display), norm_key(ref)
    if not bk or not rk:
        return None
    stmt = (
        select(WatchModel)
        .where(
            func.lower(func.trim(WatchModel.brand)) == bk,
            func.lower(func.trim(WatchModel.reference)) == rk,
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _find_by_brand_family(db: Session, brand_display: str, family: str) -> WatchModel | None:
    bk, fk = norm_key(brand_display), norm_key(family)
    if not bk or not fk:
        return None
    stmt = (
        select(WatchModel)
        .where(
            func.lower(func.trim(WatchModel.brand)) == bk,
            or_(
                WatchModel.reference.is_(None),
                func.trim(WatchModel.reference) == "",
            ),
            func.lower(func.trim(WatchModel.model_family)) == fk,
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _find_fuzzy_title(db: Session, brand_display: str, title: str | None) -> WatchModel | None:
    if not title:
        return None
    bk = norm_key(brand_display)
    if not bk:
        return None
    t = title.lower()
    stmt = select(WatchModel).where(
        func.lower(func.trim(WatchModel.brand)) == bk,
        WatchModel.model_name.isnot(None),
        func.length(func.trim(WatchModel.model_name)) >= 4,
    )
    for wm in db.scalars(stmt).all():
        mn = (wm.model_name or "").strip().lower()
        if mn and mn in t:
            return wm
    return None


def try_auto_link_listing(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
) -> None:
    if listing.watch_model_id is not None:
        return
    brand = (parsed.get("brand") or "").strip() or None
    if not brand:
        return
    ref, _ = effective_reference(parsed, edit)
    mf, _ = effective_model_family(parsed, edit)

    wm: WatchModel | None = None
    if ref:
        wm = _find_by_brand_ref(db, brand, ref)
    if wm is None and mf:
        wm = _find_by_brand_family(db, brand, mf)
    if wm is None:
        wm = _find_fuzzy_title(db, brand, listing.title)
    if wm:
        listing.watch_model_id = wm.id


def refresh_watch_model_observed_bounds(db: Session, model_id: UUID) -> None:
    wm = db.get(WatchModel, model_id)
    if not wm:
        return
    prices: list[Decimal] = []
    for p in db.scalars(
        select(Listing.current_price).where(
            Listing.watch_model_id == model_id,
            Listing.current_price.isnot(None),
        )
    ):
        if p is not None and p > 0:
            prices.append(Decimal(str(p)))

    bk = norm_key(wm.brand)
    if bk:
        sq = select(WatchSaleRecord.sale_price).where(WatchSaleRecord.brand_key == bk)
        rk = norm_key(wm.reference)
        mfk = norm_key(wm.model_family)
        if rk:
            sq = sq.where(
                or_(
                    WatchSaleRecord.reference_key == rk,
                    WatchSaleRecord.reference_key.is_(None),
                )
            )
        elif mfk:
            sq = sq.where(
                or_(
                    WatchSaleRecord.model_family_key == mfk,
                    WatchSaleRecord.model_family_key.is_(None),
                )
            )
        for p in db.scalars(sq).all():
            if p is not None and p > 0:
                prices.append(Decimal(str(p)))

    wm.observed_price_low = min(prices) if prices else None
    wm.observed_price_high = max(prices) if prices else None
    db.add(wm)
