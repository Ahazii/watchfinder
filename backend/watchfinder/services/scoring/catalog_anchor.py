"""Derive a working-market resale anchor (GBP) from watch_models catalog bounds."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class _CatalogPriceBounds(Protocol):
    manual_price_low: Decimal | None
    manual_price_high: Decimal | None
    observed_price_low: Decimal | None
    observed_price_high: Decimal | None


def working_resale_anchor_gbp(wm: _CatalogPriceBounds) -> tuple[Decimal | None, str]:
    """
    Best-effort "fixed / working watch" value in **GBP** from catalog rows.

    Priority: manual bounds (curated / WatchBase import) over observed asks from
    linked listings (which may include damaged items).
    """
    ml, mh = wm.manual_price_low, wm.manual_price_high
    ol, oh = wm.observed_price_low, wm.observed_price_high

    if ml is not None and mh is not None:
        mid = ((ml + mh) / Decimal("2")).quantize(Decimal("0.01"))
        return mid, "catalog manual £ midpoint (WatchBase / your bounds)"
    if mh is not None:
        return mh.quantize(Decimal("0.01")), "catalog manual £ high"
    if ml is not None:
        return ml.quantize(Decimal("0.01")), "catalog manual £ low"

    if ol is not None and oh is not None:
        mid = ((ol + oh) / Decimal("2")).quantize(Decimal("0.01"))
        return mid, "catalog observed £ midpoint (linked listing asks; may include this item)"
    if oh is not None:
        return oh.quantize(Decimal("0.01")), "catalog observed £ high"
    if ol is not None:
        return ol.quantize(Decimal("0.01")), "catalog observed £ low"

    return None, ""
