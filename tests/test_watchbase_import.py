"""Tests for WatchBase price JSON parsing (no network)."""

from __future__ import annotations

from watchfinder.services.watchbase_chart_json import parse_price_chart_json
from watchfinder.services.watchbase_path import guessed_watch_path, path_from_watchbase_url


def test_parse_price_chart_json() -> None:
    raw = {
        "labels": ["2018-03-27", "2019-05-01"],
        "datasets": [
            {"label": "New", "data": ["4500", "4900"]},
        ],
    }
    out = parse_price_chart_json(raw)
    assert out["currency"] == "EUR"
    assert out["source"] == "watchbase"
    assert len(out["points"]) == 2
    assert out["points"][0]["date"] == "2018-03-27"
    assert out["points"][0]["amount"] == "4500"
    assert out["points"][0]["series"] == "New"


def test_path_from_watchbase_url() -> None:
    p = path_from_watchbase_url(
        "https://watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001"
    )
    assert p == "/omega/seamaster-diver-300m/210-30-42-20-01-001"


def test_guessed_watch_path() -> None:
    g = guessed_watch_path("Omega", "Seamaster Diver 300M", "210.30.42.20.01.001")
    assert g == "/omega/seamaster-diver-300m/210-30-42-20-01-001"
