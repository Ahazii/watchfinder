"""EUR→GBP using Frankfurter (ECB) public API; optional static fallback."""

from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from watchfinder.config import Settings, get_settings

logger = logging.getLogger(__name__)

FRANKFURTER_LATEST = "https://api.frankfurter.app/latest?from=EUR&to=GBP"


def fetch_eur_to_gbp_rate(settings: Settings | None = None) -> Decimal | None:
    """
    How many GBP per 1 EUR (multiply EUR amount by this for GBP).
    Uses **EUR_GBP_RATE_FALLBACK** from settings if the API request fails.
    """
    settings = settings or get_settings()
    fb = getattr(settings, "eur_gbp_rate_fallback", None)
    try:
        ua = getattr(settings, "watchbase_import_user_agent", None) or "WatchFinder/1.0 (FX quote)"
        with httpx.Client(timeout=12.0, headers={"User-Agent": ua}) as client:
            r = client.get(FRANKFURTER_LATEST)
            r.raise_for_status()
            data = r.json()
            raw = (data.get("rates") or {}).get("GBP")
            if raw is None:
                raise ValueError("missing GBP rate")
            return Decimal(str(raw)).quantize(Decimal("0.0001"))
    except Exception as e:
        logger.warning("Frankfurter EUR→GBP failed: %s", e)
        if fb is not None:
            try:
                return Decimal(str(fb)).quantize(Decimal("0.0001"))
            except Exception:
                return None
        return None
