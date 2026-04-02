"""Assemble ListingDetail including valuation fields and comp bands."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from watchfinder.models import Listing, WatchModelLinkReview
from watchfinder.schemas.listings import (
    CompBandOut,
    ListingDetail,
    MoneyWithSourceOut,
    OpportunityScoreOut,
    ParsedAttributeOut,
    RecordedSaleOut,
    RepairSignalOut,
    ValuedStringOut,
)
from watchfinder.schemas.watch_link_reviews import WatchLinkReviewBriefOut
from watchfinder.schemas.watch_models import WatchModelBriefOut
from watchfinder.api.listing_helpers import listing_to_summary
from watchfinder.services.valuation import SOURCE_LEGEND, compute_comp_bands
from watchfinder.services.valuation.effective import (
    effective_caliber,
    effective_model_family,
    effective_reference,
    norm_key,
)
from watchfinder.services.valuation.field_help import FIELD_GUIDANCE


def _band_out(b) -> CompBandOut:
    return CompBandOut(
        count=b.count,
        p25=b.p25,
        p75=b.p75,
        low=b.low,
        high=b.high,
        label=b.label,
    )


def build_listing_detail(db: Session, listing: Listing) -> ListingDetail:
    parsed = {a.key: (a.value_text or "") for a in listing.parsed_attributes}
    edit = listing.listing_edit

    brand_val = parsed.get("brand") or None
    brand_src = "R" if brand_val else ""

    mf, mf_s = effective_model_family(parsed, edit)
    ref, ref_s = effective_reference(parsed, edit)
    cal, cal_s = effective_caliber(parsed, edit)

    sales, asking = compute_comp_bands(
        db,
        exclude_listing_id=listing.id,
        brand_display=brand_val or "",
        brand_key=norm_key(brand_val),
        model_family_key=norm_key(mf),
        _reference_key=norm_key(ref),
    )

    scores = sorted(
        listing.opportunity_scores,
        key=lambda s: s.computed_at.timestamp() if s.computed_at else 0.0,
        reverse=True,
    )
    latest_orm = scores[0] if scores else None
    summary = listing_to_summary(listing, latest_orm)

    wm = listing.watch_model
    watch_brief = WatchModelBriefOut.model_validate(wm) if wm else None

    pr = db.execute(
        select(WatchModelLinkReview).where(
            WatchModelLinkReview.listing_id == listing.id,
            WatchModelLinkReview.status == "pending",
        )
    ).scalar_one_or_none()
    pending_brief: WatchLinkReviewBriefOut | None = None
    if pr:
        pending_brief = WatchLinkReviewBriefOut(
            id=pr.id,
            tier=pr.tier,
            confidence=pr.confidence,
            candidate_count=len(pr.candidate_watch_model_ids or []),
            reason_codes=list(pr.reason_codes) if pr.reason_codes else None,
        )

    return ListingDetail(
        **summary.model_dump(),
        subtitle=listing.subtitle,
        image_urls=listing.image_urls,
        shipping_price=listing.shipping_price,
        seller_username=listing.seller_username,
        category_path=listing.category_path,
        first_seen_at=listing.first_seen_at,
        parsed_attributes=[
            ParsedAttributeOut.model_validate(x) for x in listing.parsed_attributes
        ],
        repair_signals=[RepairSignalOut.model_validate(x) for x in listing.repair_signals],
        opportunity_scores=[OpportunityScoreOut.model_validate(s) for s in scores],
        brand=ValuedStringOut(value=brand_val, source=brand_src),
        model_family=ValuedStringOut(value=mf, source=mf_s),
        reference=ValuedStringOut(value=ref, source=ref_s),
        caliber=ValuedStringOut(value=cal, source=cal_s),
        repair_supplement=MoneyWithSourceOut(
            amount=edit.repair_supplement if edit else None,
            source=(edit.repair_supplement_source or "") if edit else "",
        ),
        donor_cost=MoneyWithSourceOut(
            amount=edit.donor_cost if edit else None,
            source=(edit.donor_source or "") if edit else "",
        ),
        recorded_sale=RecordedSaleOut(
            price=edit.recorded_sale_price if edit else None,
            recorded_at=edit.recorded_sale_at if edit else None,
            source=(edit.recorded_sale_source or "") if edit else "",
        ),
        notes=edit.notes if edit else None,
        comp_sales=_band_out(sales),
        comp_asking=_band_out(asking),
        source_legend=SOURCE_LEGEND,
        field_guidance=FIELD_GUIDANCE,
        watch_model_id=listing.watch_model_id,
        watch_model=watch_brief,
        watch_link_review_pending=pending_brief,
    )
