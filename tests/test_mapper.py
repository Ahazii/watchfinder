"""Lightweight tests for ingest mappers (no DB)."""

from __future__ import annotations

from watchfinder.services.ingestion.mapper import browse_item_to_listing_fields


def test_browse_item_to_listing_fields_minimal() -> None:
    item = {
        "itemId": "v1|12345|0",
        "title": "Test watch",
        "price": {"value": "99.00", "currency": "GBP"},
        "itemWebUrl": "https://example.com/item",
        "image": {"imageUrl": "https://i.ebayimg.com/a.jpg"},
    }
    f = browse_item_to_listing_fields(item)
    assert f["ebay_item_id"] == "v1|12345|0"
    assert f["title"] == "Test watch"
    assert f["current_price"] is not None
    assert str(f["current_price"]) == "99.00"
    assert f["currency"] == "GBP"
    assert f["image_urls"] == ["https://i.ebayimg.com/a.jpg"]
