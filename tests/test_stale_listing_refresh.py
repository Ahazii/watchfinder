"""Unit tests for stale listing refresh helpers (no DB)."""

from __future__ import annotations

from watchfinder.util.app_setting_text import truthy_app_value


def test_truthy_app_value() -> None:
    assert truthy_app_value(None) is None
    assert truthy_app_value("1") is True
    assert truthy_app_value("true") is True
    assert truthy_app_value("YES") is True
    assert truthy_app_value("on") is True
    assert truthy_app_value("0") is False
    assert truthy_app_value("false") is False
    assert truthy_app_value("") is False
    assert truthy_app_value("  ") is False
    assert truthy_app_value("maybe") is None
