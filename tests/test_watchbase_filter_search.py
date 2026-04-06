"""Tests for parsing WatchBase filter/results watchesHtml (no network)."""

from __future__ import annotations

from watchfinder.services.watchbase_filter_search import parse_watches_from_filter_json

_SAMPLE_HTML = """
<a href="https://watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001" class="item-block watch-block watch-30836">
  <div class="toptext"><strong>Omega</strong> Seamaster Diver 300M</div>
  <div class="bottomtext"><strong>210.30.42.20.01.001</strong> Seamaster Diver 300M Master</div>
</a>
<div class="item-block watch-block dummy"></div>
"""


def test_parse_watches_from_filter_json() -> None:
    data = {"watchesHtml": _SAMPLE_HTML, "numWatches": 1}
    items = parse_watches_from_filter_json(data)
    assert len(items) == 1
    assert items[0]["url"] == "https://watchbase.com/omega/seamaster-diver-300m/210-30-42-20-01-001"
    assert "Omega" in items[0]["label"]
    assert "210.30" in items[0]["label"]


def test_parse_watches_empty_html() -> None:
    assert parse_watches_from_filter_json({}) == []
    assert parse_watches_from_filter_json({"watchesHtml": ""}) == []
