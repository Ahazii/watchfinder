"""Proxy search against WatchBase public filter API (`/filter/results?q=`)."""

from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

from watchfinder.config import get_settings
from watchfinder.schemas.watch_models import WatchbaseSearchHit, WatchbaseSearchResponse
from watchfinder.services.watchbase_filter_search import parse_watches_from_filter_json
from watchfinder.services.watchbase_import import DEFAULT_UA

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchbase", tags=["watchbase"])


@router.get("/search", response_model=WatchbaseSearchResponse)
def get_watchbase_search(
    q: str = Query(..., min_length=1, max_length=256, description="Search text (e.g. reference)"),
) -> WatchbaseSearchResponse:
    settings = get_settings()
    if not settings.watchbase_import_enabled:
        raise HTTPException(
            status_code=403,
            detail="WatchBase features disabled (WATCHBASE_IMPORT_ENABLED=false).",
        )
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query is empty.")

    ua = settings.watchbase_import_user_agent or DEFAULT_UA
    timeout = httpx.Timeout(20.0)
    headers = {"User-Agent": ua, "Accept": "application/json"}

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(
                "https://watchbase.com/filter/results",
                params={"q": query, "page": 1},
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        logger.warning("WatchBase filter search failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Could not reach WatchBase search. Try again later.",
        ) from e
    except json.JSONDecodeError as e:
        logger.warning("WatchBase filter invalid JSON: %s", e)
        raise HTTPException(status_code=502, detail="Unexpected response from WatchBase search.") from e

    items_raw = parse_watches_from_filter_json(data)
    items = [
        WatchbaseSearchHit(
            url=x["url"],
            label=x["label"],
            image_url=x.get("image_url"),
        )
        for x in items_raw
    ]
    total = int(data.get("numWatches") or len(items))

    return WatchbaseSearchResponse(query=query, items=items, total=total)
