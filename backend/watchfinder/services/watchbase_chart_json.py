"""Parse WatchBase public /prices Chart.js-style JSON (no DB imports)."""

from __future__ import annotations

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
