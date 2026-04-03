"""Map eBay Browse item_summary JSON into Listing fields."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def _parse_decimal(val: str | None) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        return Decimal(val)
    except Exception:
        return None


def _parse_dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        # eBay often returns Z suffix
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        return datetime.fromisoformat(iso).astimezone(UTC)
    except Exception:
        return None


def browse_item_to_listing_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Map Buy Browse **getItem** root object (same core fields as search itemSummary)."""
    return item_summary_to_listing_fields(item)


def item_summary_to_listing_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Extract columns for Listing model from one itemSummary object."""
    ebay_id = item.get("itemId")
    if not ebay_id:
        raise ValueError("itemSummary missing itemId")

    price_block = item.get("price") or {}
    ship_block = item.get("shippingOptions") or []
    ship_price = None
    if ship_block and isinstance(ship_block, list):
        first = ship_block[0] if ship_block else {}
        sc = first.get("shippingCost") if isinstance(first, dict) else None
        if isinstance(sc, dict):
            ship_price = _parse_decimal(sc.get("value"))

    images = item.get("image") or {}
    img_url = images.get("imageUrl") if isinstance(images, dict) else None
    thumbs = item.get("thumbnailImages") or []
    image_urls: list[str] = []
    if img_url:
        image_urls.append(img_url)
    for t in thumbs:
        if isinstance(t, dict) and t.get("imageUrl"):
            image_urls.append(t["imageUrl"])

    seller = item.get("seller") or {}
    seller_username = seller.get("username") if isinstance(seller, dict) else None

    cond = item.get("condition") or {}
    condition_id = cond.get("conditionId") if isinstance(cond, dict) else None
    condition_text = None
    if isinstance(cond, dict):
        condition_text = cond.get("conditionDisplayName")

    cats = item.get("categories") or []
    category_path = None
    if cats and isinstance(cats, list):
        names = [c.get("categoryName") for c in cats if isinstance(c, dict)]
        category_path = " > ".join(n for n in names if n)

    buying = item.get("buyingOptions")
    if buying is not None and not isinstance(buying, list):
        buying = [buying] if buying else []

    return {
        "ebay_item_id": str(ebay_id),
        "title": item.get("title"),
        "subtitle": None,
        "web_url": item.get("itemWebUrl"),
        "image_urls": image_urls or None,
        "current_price": _parse_decimal(price_block.get("value")),
        "shipping_price": ship_price,
        "currency": price_block.get("currency"),
        "seller_username": seller_username,
        "condition_id": str(condition_id) if condition_id is not None else None,
        "condition_description": condition_text,
        "buying_options": buying,
        "category_path": category_path,
        "listing_started_at": _parse_dt(item.get("itemCreationDate")),
        "listing_ended_at": _parse_dt(item.get("itemEndDate")),
        "item_aspects": item.get("localizedAspects"),
        "raw_item_json": item,
    }
