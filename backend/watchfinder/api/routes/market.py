"""Unified market search (WatchBase + Everywatch + Chrono24 metadata)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from watchfinder.config import get_settings
from watchfinder.schemas.watch_models import UnifiedMarketSearchResponse
from watchfinder.services.market_unified_search import unified_market_search

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/search", response_model=UnifiedMarketSearchResponse)
def get_market_search(
    q: str = Query(..., min_length=1, max_length=320, description="Primary search text (e.g. brand + reference)"),
    brand: str | None = Query(None, max_length=255, description="Improves Everywatch URL guess"),
    reference: str | None = Query(None, max_length=128),
    model_family: str | None = Query(None, max_length=512),
) -> UnifiedMarketSearchResponse:
    settings = get_settings()
    data = unified_market_search(
        q=q,
        brand=brand,
        reference=reference,
        model_family=model_family,
        settings=settings,
    )
    return UnifiedMarketSearchResponse.model_validate(data)
