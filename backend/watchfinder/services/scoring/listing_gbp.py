"""Convert listing ask to GBP for catalog-based profit math (Frankfurter ECB rates)."""

from __future__ import annotations

import logging
import time
from decimal import Decimal

import httpx

from watchfinder.config import Settings, get_settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 3600.0
_rate_cache: dict[str, tuple[float, Decimal]] = {}


def _cache_get(code: str) -> Decimal | None:
    ent = _rate_cache.get(code)
    if not ent:
        return None
    ts, rate = ent
    if time.monotonic() - ts > _CACHE_TTL_SEC:
        del _rate_cache[code]
        return None
    return rate


def _cache_set(code: str, rate: Decimal) -> None:
    _rate_cache[code] = (time.monotonic(), rate)


def gbp_per_unit_of(currency_code: str | None, settings: Settings | None = None) -> Decimal | None:
    """
    How many GBP one unit of ``currency_code`` is worth (multiply price by this for GBP).

    Uses Frankfurter ``latest?from={code}&to=GBP`` with a 1h process-local cache.
    Returns ``Decimal('1')`` for GBP. ``None`` if unsupported or request fails.
    """
    settings = settings or get_settings()
    c = (currency_code or "GBP").strip().upper() or "GBP"
    if c == "GBP":
        return Decimal("1")

    hit = _cache_get(c)
    if hit is not None:
        return hit

    ua = getattr(settings, "watchbase_import_user_agent", None) or "WatchFinder/1.0 (FX quote)"
    url = f"https://api.frankfurter.app/latest?from={c}&to=GBP"
    try:
        with httpx.Client(
            timeout=12.0,
            headers={"User-Agent": ua},
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json()
            raw = (data.get("rates") or {}).get("GBP")
            if raw is None:
                raise ValueError("missing GBP rate")
            rate = Decimal(str(raw)).quantize(Decimal("0.0001"))
            _cache_set(c, rate)
            return rate
    except Exception as e:
        logger.warning("Frankfurter %s→GBP failed: %s", c, e)
        return None


def listing_ask_gbp(
    price: Decimal,
    currency_code: str | None,
    settings: Settings | None = None,
) -> tuple[Decimal | None, str]:
    """Return (ask_in_gbp, note) or (None, reason)."""
    if price <= 0:
        return None, "no list price"
    rate = gbp_per_unit_of(currency_code, settings)
    if rate is None:
        c = (currency_code or "GBP").strip().upper() or "GBP"
        return None, f"no FX rate for {c}→GBP (catalog comparison skipped)"
    gbp = (price * rate).quantize(Decimal("0.01"))
    c = (currency_code or "GBP").strip().upper() or "GBP"
    note = f"asking price → GBP: {price} {c} × {rate} = {gbp}"
    return gbp, note
