"""Resolve listing identity to brands / calibers / stock references (fuzzy + inference)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from watchfinder.models import (
    Brand,
    Caliber,
    CaliberBrandLink,
    CaliberStockReferenceLink,
    Listing,
    ListingCaliber,
    ListingEdit,
    StockReference,
)
from watchfinder.services.entities.normalize import normalize_entity_key
from watchfinder.services.valuation.effective import effective_caliber, effective_reference


@dataclass
class EntityResolveResult:
    reason_codes: list[str] = field(default_factory=list)
    inferred_brand_display: str | None = None


# Tunable fuzzy thresholds (0–100)
_BRAND_SCORE = 88
_REF_SCORE = 82
_CAL_SCORE = 82


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _get_or_create_brand(db: Session, display: str) -> Brand:
    nk = normalize_entity_key(display)
    if not nk:
        raise ValueError("empty brand")
    row = db.scalar(select(Brand).where(Brand.norm_key == nk))
    if row:
        return row
    all_b = db.scalars(select(Brand)).all()
    if all_b:
        choices = [b.display_name for b in all_b]
        hit = process.extractOne(
            display.strip(),
            choices,
            scorer=fuzz.WRatio,
            score_cutoff=_BRAND_SCORE,
        )
        if hit:
            _, score, idx = hit
            if score >= _BRAND_SCORE:
                return all_b[idx]
    b = Brand(display_name=display.strip(), norm_key=nk)
    db.add(b)
    db.flush()
    return b


def _get_or_create_caliber(db: Session, raw: str) -> Caliber:
    nk = normalize_entity_key(raw)
    if not nk:
        raise ValueError("empty caliber")
    row = db.scalar(select(Caliber).where(Caliber.norm_key == nk))
    if row:
        return row
    all_c = db.scalars(select(Caliber)).all()
    if all_c:
        choices = [c.display_text for c in all_c]
        hit = process.extractOne(
            raw.strip(),
            choices,
            scorer=fuzz.WRatio,
            score_cutoff=_CAL_SCORE,
        )
        if hit:
            _, score, idx = hit
            if score >= _CAL_SCORE:
                return all_c[idx]
    c = Caliber(display_text=raw.strip(), norm_key=nk)
    db.add(c)
    db.flush()
    return c


def _get_or_create_stock_reference(
    db: Session, brand_id: uuid.UUID, ref_raw: str, watch_model_id: uuid.UUID | None
) -> StockReference:
    nk = normalize_entity_key(ref_raw)
    if not nk:
        raise ValueError("empty reference")
    row = db.scalar(
        select(StockReference).where(
            StockReference.brand_id == brand_id,
            StockReference.norm_key == nk,
        )
    )
    if row:
        if watch_model_id and row.watch_model_id is None:
            row.watch_model_id = watch_model_id
        return row
    brand_refs = db.scalars(
        select(StockReference).where(StockReference.brand_id == brand_id)
    ).all()
    if brand_refs:
        choices = [r.ref_text for r in brand_refs]
        hit = process.extractOne(
            ref_raw.strip(),
            choices,
            scorer=fuzz.WRatio,
            score_cutoff=_REF_SCORE,
        )
        if hit:
            _, score, idx = hit
            if score >= _REF_SCORE:
                got = brand_refs[idx]
                if watch_model_id and got.watch_model_id is None:
                    got.watch_model_id = watch_model_id
                return got
    sr = StockReference(
        brand_id=brand_id,
        ref_text=ref_raw.strip(),
        norm_key=nk,
        watch_model_id=watch_model_id,
    )
    db.add(sr)
    db.flush()
    return sr


def _ensure_caliber_brand(db: Session, caliber_id: uuid.UUID, brand_id: uuid.UUID) -> None:
    row = db.scalar(
        select(CaliberBrandLink).where(
            CaliberBrandLink.caliber_id == caliber_id,
            CaliberBrandLink.brand_id == brand_id,
        )
    )
    if row is None:
        db.add(CaliberBrandLink(caliber_id=caliber_id, brand_id=brand_id))
        db.flush()


def _ensure_caliber_stock_ref(
    db: Session, caliber_id: uuid.UUID, stock_reference_id: uuid.UUID
) -> None:
    row = db.scalar(
        select(CaliberStockReferenceLink).where(
            CaliberStockReferenceLink.caliber_id == caliber_id,
            CaliberStockReferenceLink.stock_reference_id == stock_reference_id,
        )
    )
    if row is None:
        db.add(
            CaliberStockReferenceLink(
                caliber_id=caliber_id, stock_reference_id=stock_reference_id
            )
        )
        db.flush()


def _infer_brand_from_caliber_and_reference(
    db: Session, cal_raw: str | None, ref_raw: str | None
) -> tuple[Brand | None, bool]:
    """If exactly one brand in DB matches caliber+reference fuzzy links, return it."""
    if not (cal_raw and str(cal_raw).strip() and ref_raw and str(ref_raw).strip()):
        return None, False
    cal_clean = cal_raw.strip()
    ref_clean = ref_raw.strip()
    all_cal = db.scalars(select(Caliber)).all()
    if not all_cal:
        return None, False
    cal_choices = [c.display_text for c in all_cal]
    cal_hit = process.extractOne(
        cal_clean, cal_choices, scorer=fuzz.WRatio, score_cutoff=_CAL_SCORE
    )
    if not cal_hit:
        return None, False
    _, cal_score, cal_idx = cal_hit
    if cal_score < _CAL_SCORE:
        return None, False
    caliber = all_cal[cal_idx]

    stmt = (
        select(StockReference, Brand)
        .join(CaliberStockReferenceLink, CaliberStockReferenceLink.stock_reference_id == StockReference.id)
        .join(Brand, Brand.id == StockReference.brand_id)
        .where(CaliberStockReferenceLink.caliber_id == caliber.id)
    )
    pairs = db.execute(stmt).all()
    if not pairs:
        return None, False

    brand_ids: set[uuid.UUID] = set()
    for sr, br in pairs:
        rscore = fuzz.WRatio(ref_clean, sr.ref_text)
        if rscore >= _REF_SCORE:
            brand_ids.add(br.id)

    if len(brand_ids) == 1:
        bid = next(iter(brand_ids))
        b = db.get(Brand, bid)
        return (b, False)
    if len(brand_ids) > 1:
        return (None, True)
    return (None, False)


def resolve_listing_entities(
    db: Session,
    listing: Listing,
    parsed: dict[str, str],
    edit: ListingEdit | None,
) -> EntityResolveResult:
    reasons: list[str] = []
    inferred: str | None = None

    db.execute(delete(ListingCaliber).where(ListingCaliber.listing_id == listing.id))
    listing.resolved_brand_id = None
    listing.resolved_stock_reference_id = None

    brand_raw = (parsed.get("brand") or "").strip() or None
    ref_raw, _ = effective_reference(parsed, edit)
    ref_raw = (ref_raw or "").strip() or None
    cal_raw, _ = effective_caliber(parsed, edit)
    cal_raw = (cal_raw or "").strip() or None

    brand: Brand | None = None
    if brand_raw:
        brand = _get_or_create_brand(db, brand_raw)
    elif cal_raw and ref_raw:
        inferred_br, ambiguous = _infer_brand_from_caliber_and_reference(db, cal_raw, ref_raw)
        if inferred_br:
            brand = inferred_br
            inferred = inferred_br.display_name
            parsed["brand"] = inferred
            reasons.append("entity_brand_inferred_from_caliber_reference")
        elif ambiguous:
            reasons.append("entity_brand_ambiguous")

    if brand is None and (ref_raw or cal_raw):
        reasons.append("entity_brand_unresolved")

    if brand is not None:
        listing.resolved_brand_id = brand.id

    watch_mid = listing.watch_model_id

    stock_ref: StockReference | None = None
    if brand is not None and ref_raw:
        try:
            stock_ref = _get_or_create_stock_reference(db, brand.id, ref_raw, watch_mid)
            listing.resolved_stock_reference_id = stock_ref.id
        except ValueError:
            reasons.append("entity_reference_invalid")

    cal_obj: Caliber | None = None
    if cal_raw:
        try:
            cal_obj = _get_or_create_caliber(db, cal_raw)
            db.add(ListingCaliber(listing_id=listing.id, caliber_id=cal_obj.id))
        except ValueError:
            reasons.append("entity_caliber_invalid")

    if brand is not None and cal_obj is not None:
        _ensure_caliber_brand(db, cal_obj.id, brand.id)

    if cal_obj is not None and stock_ref is not None:
        _ensure_caliber_stock_ref(db, cal_obj.id, stock_ref.id)

    if stock_ref is not None and watch_mid and stock_ref.watch_model_id is None:
        stock_ref.watch_model_id = watch_mid

    db.flush()
    return EntityResolveResult(
        reason_codes=_dedupe_preserve(reasons),
        inferred_brand_display=inferred,
    )


def backfill_entity_dictionaries(db: Session) -> dict[str, int]:
    """Re-parse active listings and resolve brands/calibers/stock references (no full catalog pass)."""
    from sqlalchemy import select

    from watchfinder.services.listing_status import active_listing_clause
    from watchfinder.services.parsing import build_listing_corpus, parse_watch_attributes

    stats = {
        "scanned": 0,
        "with_resolved_brand": 0,
        "with_resolved_reference": 0,
        "with_caliber_link": 0,
        "inferred_brand": 0,
    }
    stmt = (
        select(Listing)
        .where(active_listing_clause())
        .order_by(Listing.last_seen_at.desc())
    )
    for listing in db.scalars(stmt).all():
        corpus = build_listing_corpus(listing)
        parsed = parse_watch_attributes(listing.title or "", corpus)
        edit = db.get(ListingEdit, listing.id)
        res = resolve_listing_entities(db, listing, parsed, edit)
        stats["scanned"] += 1
        if listing.resolved_brand_id is not None:
            stats["with_resolved_brand"] += 1
        if listing.resolved_stock_reference_id is not None:
            stats["with_resolved_reference"] += 1
        if res.inferred_brand_display:
            stats["inferred_brand"] += 1
        n_lc = db.scalar(
            select(func.count())
            .select_from(ListingCaliber)
            .where(ListingCaliber.listing_id == listing.id)
        )
        if n_lc and int(n_lc) > 0:
            stats["with_caliber_link"] += 1
    return stats
