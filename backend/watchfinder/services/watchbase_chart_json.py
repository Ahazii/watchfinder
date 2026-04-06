"""Parse WatchBase public /prices Chart.js-style JSON (no DB imports)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def parse_price_chart_json(data: dict[str, Any]) -> dict[str, Any]:
    """Chart.js-style /prices payload -> storable shape (EUR list prices)."""
    labels = data.get("labels") or []
    points: list[dict[str, str]] = []
    for ds in data.get("datasets") or []:
        series = str(ds.get("label") or "Price")
        values = ds.get("data") or []
        for i, v in enumerate(values):
            if i < len(labels):
                points.append(
                    {
                        "date": str(labels[i]),
                        "amount": str(v),
                        "series": series,
                    }
                )
    return {
        "source": "watchbase",
        "currency": "EUR",
        "points": points,
    }


def min_max_eur_from_price_history(hist: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    """Min/max over all numeric **amount** values in stored history (EUR list prices)."""
    points = hist.get("points") or []
    amounts: list[Decimal] = []
    for p in points:
        raw = p.get("amount")
        if raw is None:
            continue
        s = str(raw).strip().replace(",", "")
        if not s:
            continue
        try:
            amounts.append(Decimal(s))
        except InvalidOperation:
            continue
    if not amounts:
        return None
    return min(amounts), max(amounts)
