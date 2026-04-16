"""Heuristic listing type classification."""

from __future__ import annotations

from unittest.mock import MagicMock

from watchfinder.services.listing_type_infer import infer_listing_type


def _listing(category: str | None = None) -> MagicMock:
    m = MagicMock()
    m.title = None
    m.category_path = category
    return m


def test_movement_only_strong_phrase():
    t = infer_listing_type(
        _listing(),
        "ETA 2824-2 movement only — no case",
        "sold as-is for parts",
        {},
    )
    assert t == "movement_only"


def test_parts_dial():
    t = infer_listing_type(
        _listing(),
        "Rolex dial only genuine",
        "",
        {},
    )
    assert t == "parts_other"


def test_complete_watch():
    t = infer_listing_type(
        _listing(),
        "Omega Seamaster 300m complete watch box and papers",
        "",
        {},
    )
    assert t == "watch_complete"


def test_unknown_when_ambiguous():
    t = infer_listing_type(
        _listing(),
        "ETA movement only — complete watch wristwatch box and papers",
        "",
        {},
    )
    assert t == "unknown"
