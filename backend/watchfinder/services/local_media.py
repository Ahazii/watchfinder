"""Download eBay listing gallery images into LOCAL_MEDIA_ROOT; serve under /api/media/...."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from watchfinder.config import Settings, get_settings

logger = logging.getLogger(__name__)

LOCAL_URL_PREFIX = "/api/media/"
MAX_IMAGE_BYTES = 6 * 1024 * 1024
DOWNLOAD_TIMEOUT = 20.0
DEFAULT_UA = "WatchFinder/1.0 (catalog image cache; listing gallery)"

_CT_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _media_root(settings: Settings) -> Path:
    return Path(settings.local_media_root).expanduser().resolve()


def watch_model_has_local_cached_image(wm: Any) -> bool:
    for u in wm.image_urls or []:
        if isinstance(u, str) and u.strip().startswith(LOCAL_URL_PREFIX):
            return True
    return False


def _is_probably_ebay_image_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return "ebay" in host


def watch_model_should_copy_listing_image(wm: Any) -> bool:
    """
    Copy when the model has no images, only eBay CDN URLs, or already only our cache paths
    (re-copy skipped by **has_local_cached**).
    Do not overwrite a catalog that already has non-eBay external images (e.g. WatchBase).
    """
    if watch_model_has_local_cached_image(wm):
        return False
    urls = [u.strip() for u in (wm.image_urls or []) if isinstance(u, str) and u.strip()]
    if not urls:
        return True
    return all(_is_probably_ebay_image_url(u) for u in urls)


def first_listing_gallery_image_url(listing: Any) -> str | None:
    for u in listing.image_urls or []:
        if isinstance(u, str):
            t = u.strip()
            if t.startswith(("http://", "https://")):
                return t
    return None


def _extension_from_content_type(ct: str | None) -> str | None:
    if not ct:
        return None
    base = ct.split(";")[0].strip().lower()
    return _CT_EXT.get(base)


def _extension_from_url(url: str) -> str | None:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return None


def _safe_filename_suffix_from_url(url: str) -> str:
    ext = _extension_from_url(url) or ".jpg"
    return ext if re.match(r"^\.[a-z0-9]{2,5}$", ext, re.I) else ".jpg"


def download_image_bytes(url: str, user_agent: str | None) -> tuple[bytes, str]:
    headers = {"User-Agent": user_agent or DEFAULT_UA, "Accept": "image/*,*/*;q=0.8"}
    with httpx.Client(timeout=httpx.Timeout(DOWNLOAD_TIMEOUT), follow_redirects=True) as client:
        with client.stream("GET", url, headers=headers) as r:
            r.raise_for_status()
            ct = r.headers.get("content-type")
            chunks: list[bytes] = []
            total = 0
            for block in r.iter_bytes():
                total += len(block)
                if total > MAX_IMAGE_BYTES:
                    raise ValueError("image too large")
                chunks.append(block)
            data = b"".join(chunks)
    ext = _extension_from_content_type(ct) or _safe_filename_suffix_from_url(url)
    if ext == ".jpeg":
        ext = ".jpg"
    return data, ext


def write_watch_model_primary_image(
    settings: Settings,
    watch_model_id: UUID,
    body: bytes,
    ext: str,
) -> str:
    """Write bytes to disk; return public path ``/api/media/watch_models/{id}/primary.{ext}``."""
    root = _media_root(settings)
    rel_dir = Path("watch_models") / str(watch_model_id)
    dest_dir = root / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    for old in dest_dir.glob("primary.*"):
        try:
            old.unlink()
        except OSError:
            pass
    ext = ext if ext.startswith(".") else f".{ext}"
    dest = dest_dir / f"primary{ext}"
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    rel = rel_dir.as_posix() + f"/primary{ext}"
    return f"{LOCAL_URL_PREFIX}{rel}"


def enrich_watch_model_image_from_listing(
    db: Session,
    listing: Any,
    settings: Settings | None = None,
) -> None:
    """If the linked watch model should cache an eBay image, download and set **image_urls**."""
    from watchfinder.models import WatchModel

    settings = settings or get_settings()
    if not settings.media_download_enabled:
        return
    if listing.watch_model_id is None:
        return

    wm = db.get(WatchModel, listing.watch_model_id)
    if wm is None:
        return
    if not watch_model_should_copy_listing_image(wm):
        return
    src = first_listing_gallery_image_url(listing)
    if not src:
        return
    try:
        body, ext = download_image_bytes(src, settings.media_download_user_agent)
    except Exception as e:
        logger.warning(
            "Could not cache listing image for watch_model_id=%s from %s: %s",
            wm.id,
            src[:120],
            e,
        )
        return
    try:
        public = write_watch_model_primary_image(settings, wm.id, body, ext)
    except OSError as e:
        logger.warning("Could not write media for watch_model_id=%s: %s", wm.id, e)
        return
    wm.image_urls = [public]
    db.add(wm)
