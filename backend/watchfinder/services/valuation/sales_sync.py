"""Keep watch_sale_records in sync when user records a sale on a listing."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from watchfinder.models import Listing, ListingEdit, WatchSaleRecord
from watchfinder.services.valuation.effective import (
    effective_caliber,
    effective_model_family,
    effective_reference,
    norm_key,
)


def sync_watch_sale_record(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
) -> None:
    """Replace sale comp row for this listing when price is set; else remove."""
    if edit is None:
        return
    db.execute(delete(WatchSaleRecord).where(WatchSaleRecord.listing_id == listing.id))
    price = edit.recorded_sale_price
    if price is None or price <= 0:
        db.flush()
        return
    brand = (parsed.get("brand") or "").strip()
    if not brand:
        db.flush()
        return
    mf, _ = effective_model_family(parsed, edit)
    ref, _ = effective_reference(parsed, edit)
    cal, _ = effective_caliber(parsed, edit)
    src = (edit.recorded_sale_source or "M")[:1]
    db.add(
        WatchSaleRecord(
            id=uuid.uuid4(),
            listing_id=listing.id,
            ebay_item_id=listing.ebay_item_id,
            brand_key=norm_key(brand) or "unknown",
            model_family_key=norm_key(mf),
            reference_key=norm_key(ref),
            caliber_key=norm_key(cal),
            sale_price=Decimal(price),
            currency=(listing.currency or "GBP")[:8],
            source=src,
        )
    )
    db.flush()
