from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sqlalchemy import and_, or_

from watchfinder.models import Listing


def active_listing_clause():
    """Listing is active flag + not ended by eBay end timestamp."""
    return and_(
        Listing.is_active.is_(True),
        or_(Listing.listing_ended_at.is_(None), Listing.listing_ended_at > datetime.now(UTC)),
    )


def inactive_listing_clause():
    """Listing is explicitly inactive or ended by eBay end timestamp."""
    return or_(
        Listing.is_active.is_(False),
        Listing.listing_ended_at <= datetime.now(UTC),
    )


def compute_is_effectively_active(ended_at: datetime | None, *, now: datetime | None = None) -> bool:
    if ended_at is None:
        return True
    current = now or datetime.now(UTC)
    return ended_at > current


def recompute_all_listing_is_active(db: Session) -> dict[str, int]:
    now = datetime.now(UTC)
    total = int(db.scalar(select(func.count()).select_from(Listing)) or 0)
    updated = 0
    active_now = 0
    inactive_now = 0
    for listing in db.scalars(select(Listing)).all():
        effective = compute_is_effectively_active(listing.listing_ended_at, now=now)
        if listing.is_active != effective:
            listing.is_active = effective
            updated += 1
        if effective:
            active_now += 1
        else:
            inactive_now += 1
    db.commit()
    return {
        "total": total,
        "updated": updated,
        "active_now": active_now,
        "inactive_now": inactive_now,
    }
