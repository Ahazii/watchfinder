"""Local media helpers for watch catalog images."""

from __future__ import annotations

from types import SimpleNamespace

from watchfinder.services.local_media import (
    watch_model_has_local_cached_image,
    watch_model_should_copy_listing_image,
)


def test_watch_model_should_copy_when_empty() -> None:
    wm = SimpleNamespace(image_urls=None)
    assert watch_model_should_copy_listing_image(wm) is True


def test_watch_model_skip_when_local_cached() -> None:
    wm = SimpleNamespace(image_urls=["/api/media/watch_models/x/primary.jpg"])
    assert watch_model_has_local_cached_image(wm) is True
    assert watch_model_should_copy_listing_image(wm) is False


def test_watch_model_copy_when_only_ebay_urls() -> None:
    wm = SimpleNamespace(image_urls=["https://i.ebayimg.com/images/g/xx/s-l500.jpg"])
    assert watch_model_should_copy_listing_image(wm) is True


def test_watch_model_skip_when_watchbase_url() -> None:
    wm = SimpleNamespace(image_urls=["https://cdn.watchbase.com/watch/md/x.png"])
    assert watch_model_should_copy_listing_image(wm) is False
