"""Server-side ordering for listing list endpoints (latest opportunity score per row)."""

from __future__ import annotations

from sqlalchemy import Select, func, nulls_last, select

from watchfinder.models import Listing, OpportunityScore

ALLOWED_SORT = frozenset({"last_seen", "title", "price", "confidence", "profit"})


def normalize_sort(sort_by: str | None, sort_dir: str | None) -> tuple[str, bool]:
    """Return (column_key, descending)."""
    key = (sort_by or "last_seen").strip().lower()
    if key not in ALLOWED_SORT:
        key = "last_seen"
    d = (sort_dir or "desc").strip().lower()
    desc = d != "asc"
    return key, desc


def _latest_score_scalar(column):
    return (
        select(column)
        .where(OpportunityScore.listing_id == Listing.id)
        .order_by(OpportunityScore.computed_at.desc())
        .limit(1)
        .scalar_subquery()
    )


def _tie():
    return Listing.id.asc()


def apply_listing_sort(stmt: Select, *, sort_by: str, descending: bool) -> Select:
    if sort_by == "last_seen":
        col = Listing.last_seen_at
        o = col.desc().nulls_last() if descending else col.asc().nulls_last()
        return stmt.order_by(o, _tie())
    if sort_by == "title":
        col = func.lower(func.coalesce(Listing.title, ""))
        o = col.desc().nulls_last() if descending else col.asc().nulls_last()
        return stmt.order_by(o, _tie())
    if sort_by == "price":
        col = Listing.current_price
        o = col.desc().nulls_last() if descending else col.asc().nulls_last()
        return stmt.order_by(o, _tie())
    if sort_by == "confidence":
        sq = _latest_score_scalar(OpportunityScore.confidence)
        o = sq.desc().nulls_last() if descending else sq.asc().nulls_last()
        return stmt.order_by(o, _tie())
    if sort_by == "profit":
        sq = _latest_score_scalar(OpportunityScore.potential_profit)
        o = sq.desc().nulls_last() if descending else sq.asc().nulls_last()
        return stmt.order_by(o, _tie())
    col = Listing.last_seen_at
    return stmt.order_by(col.desc().nulls_last(), _tie())
