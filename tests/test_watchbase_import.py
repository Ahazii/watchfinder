"""Tests for WatchBase price JSON parsing (no network)."""

from __future__ import annotations

from decimal import Decimal

from watchfinder.services.watchbase_chart_json import (
    min_max_eur_from_price_history,
    parse_price_chart_json,
)
from watchfinder.services.watchbase_path import guessed_watch_path, path_from_watchbase_url


def test_min_max_eur_from_price_history() -> None:
    hist = {
        "source": "watchbase",
        "currency": "EUR",
        "points": [
            {"date": "2020-01-01", "amount": "1000", "series": "New"},
            {"date": "2021-01-01", "amount": "2,500.50", "series": "New"},
        ],
    }
    lo, hi = min_max_eur_from_price_history(hist)
    assert lo == Decimal("1000")
    assert hi == Decimal("2500.50")


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


def test_path_from_watchbase_url_trailing_space() -> None:
    p = path_from_watchbase_url(
        "https://watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001 "
    )
    assert p == "/omega/seamaster-diver-300m/210-30-42-20-01-001"


def test_path_from_watchbase_url_no_scheme() -> None:
    p = path_from_watchbase_url(
        "watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001"
    )
    assert p == "/omega/seamaster-diver-300m/210-30-42-20-01-001"


def test_path_from_watchbase_url_path_only() -> None:
    p = path_from_watchbase_url("/omega/seamaster-diver-300m/210-30-42-20-01-001")
    assert p == "/omega/seamaster-diver-300m/210-30-42-20-01-001"


def test_guessed_watch_path() -> None:
    g = guessed_watch_path("Omega", "Seamaster Diver 300M", "210.30.42.20.01.001")
    assert g == "/omega/seamaster-diver-300m/210-30-42-20-01-001"
