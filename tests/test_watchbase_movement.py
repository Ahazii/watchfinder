"""Caliber extraction from WatchBase Movement row."""

from __future__ import annotations

from watchfinder.services.watchbase_movement import (
    caliber_from_movement_td,
    caliber_from_watchbase_watch_html,
)


def test_caliber_from_movement_link_href() -> None:
    html = """<table class="info-table"><tr><th>Movement</th><td>
    <a href="https://watchbase.com/omega/caliber/8800">Omega caliber 8800</a>
    Hours, Minutes, Seconds | Date
    </td></tr></table>"""
    assert caliber_from_watchbase_watch_html(html) == "8800"


def test_caliber_from_movement_plain_text() -> None:
    html = """<table class="info-table"><tr><th>Movement</th><td>
    Rolex caliber 3235 Automatic
    </td></tr></table>"""
    assert caliber_from_watchbase_watch_html(html) == "3235"


def test_caliber_from_movement_cal_abbrev() -> None:
    from bs4 import BeautifulSoup

    td = BeautifulSoup(
        "<td>ETA cal. 2824-2 automatic</td>",
        "html.parser",
    ).td
    assert caliber_from_movement_td(td) == "2824-2"


def test_caliber_no_movement_row() -> None:
    assert caliber_from_watchbase_watch_html("<table class='info-table'></table>") is None
