"""Aggregate WatchBase + Everywatch + Chrono24 links for the Find-on-market UI."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from watchfinder.config import Settings, get_settings
from watchfinder.services.chrono24_client import (
    chrono24_google_site_url,
    chrono24_search_url,
    try_fetch_chrono24_search,
)
from watchfinder.services.everywatch_client import collect_everywatch_snapshot
from watchfinder.services.watchbase_filter_search import parse_watches_from_filter_json
from watchfinder.services.watchbase_import import DEFAULT_UA

logger = logging.getLogger(__name__)


def fetch_watchbase_items(q: str, settings: Settings) -> tuple[list[dict[str, Any]], int]:
    if not settings.watchbase_import_enabled or not (q or "").strip():
        return [], 0
    ua = settings.watchbase_import_user_agent or DEFAULT_UA
    try:
        with httpx.Client(
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            headers={"User-Agent": ua, "Accept": "application/json"},
        ) as client:
            r = client.get(
                "https://watchbase.com/filter/results",
                params={"q": q.strip(), "page": 1},
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        logger.warning("WatchBase unified search failed: %s", e)
        return [], 0
    items = parse_watches_from_filter_json(data)
    total = int(data.get("numWatches") or len(items))
    return items, total


def everywatch_search_hits(
    brand: str | None,
    reference: str | None,
    model_family: str | None,
    settings: Settings,
    *,
    everywatch_url: str | None = None,
) -> list[dict[str, Any]]:
    if not (brand or "").strip() and not (everywatch_url or "").strip():
        return []
    snap = collect_everywatch_snapshot(
        (brand or "").strip() or "",
        (reference or None),
        (model_family or None),
        settings=settings,
        everywatch_url=everywatch_url,
    )
    hits = snap.get("hits") or []
    out: list[dict[str, Any]] = []
    for h in hits[:24]:
        label = h.get("label") or ""
        price_hint = None
        if h.get("amount") and h.get("currency"):
            price_hint = f"{h['amount']} {h['currency']}"
        out.append(
            {
                "url": h.get("url"),
                "label": label[:400],
                "image_url": None,
                "price_hint": price_hint,
            }
        )
    return [x for x in out if x.get("url")]


def unified_market_search(
    *,
    q: str,
    brand: str | None = None,
    reference: str | None = None,
    model_family: str | None = None,
    everywatch_url: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    qn = (q or "").strip()
    wb_raw, wb_total = fetch_watchbase_items(qn, settings)
    wb_items = [
        {"url": x["url"], "label": x["label"], "image_url": x.get("image_url"), "price_hint": None}
        for x in wb_raw[:24]
    ]

    ew_items = everywatch_search_hits(
        brand,
        reference,
        model_family,
        settings,
        everywatch_url=everywatch_url,
    )

    c24_q = qn or " ".join(
        p for p in [(brand or "").strip(), (reference or "").strip(), (model_family or "").strip()] if p
    )
    c24_hits, c24_err = try_fetch_chrono24_search(c24_q, settings=settings) if c24_q else ([], None)
    c24_ui = [
        {"url": h["url"], "label": h.get("label") or h["url"], "image_url": None, "price_hint": None}
        for h in c24_hits[:20]
    ]

    return {
        "query": qn,
        "watchbase": {"items": wb_items, "total": wb_total},
        "everywatch": {"items": ew_items},
        "chrono24": {
            "items": c24_ui,
            "search_url": chrono24_search_url(c24_q, uk=True) if c24_q else "",
            "google_site_url": chrono24_google_site_url(c24_q) if c24_q else "",
            "error": c24_err,
        },
    }
