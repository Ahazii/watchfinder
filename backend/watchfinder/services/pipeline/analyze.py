"""Re-parse, re-signal, re-score a single listing (after ingest)."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from watchfinder.models import (
    Listing,
    ListingEdit,
    OpportunityScore,
    ParsedAttribute,
    RepairSignal,
    WatchModel,
)
from watchfinder.services.entities.resolve import resolve_listing_entities
from watchfinder.services.parsing import build_listing_corpus, parse_watch_attributes
from watchfinder.services.repair import extract_repair_signals
from watchfinder.services.scoring import compute_opportunity_score
from watchfinder.config import get_settings
from watchfinder.services.local_media import enrich_watch_model_image_from_listing
from watchfinder.services.market_snapshots import maybe_refresh_market_snapshots_for_model
from watchfinder.services.watch_models import (
    ensure_watch_catalog_for_listing,
    refresh_watch_model_observed_bounds,
)
from watchfinder.services.watch_models.catalog import CatalogLinkOutcome
from watchfinder.services.listing_type_infer import maybe_apply_auto_listing_type


def analyze_listing(db: Session, listing: Listing) -> CatalogLinkOutcome:
    corpus = build_listing_corpus(listing)
    parsed = parse_watch_attributes(listing.title, corpus)
    signals = extract_repair_signals(corpus)
    edit = db.get(ListingEdit, listing.id)
    entity_res = resolve_listing_entities(db, listing, parsed, edit)

    db.execute(delete(ParsedAttribute).where(ParsedAttribute.listing_id == listing.id))
    db.execute(delete(RepairSignal).where(RepairSignal.listing_id == listing.id))
    db.execute(delete(OpportunityScore).where(OpportunityScore.listing_id == listing.id))

    for k, v in parsed.items():
        db.add(
            ParsedAttribute(
                listing_id=listing.id,
                namespace="watch",
                key=k,
                value_text=v,
            )
        )

    for s in signals:
        db.add(
            RepairSignal(
                listing_id=listing.id,
                signal_type=s.signal_type,
                matched_text=s.matched_text,
                source_field=s.source_field,
            )
        )

    maybe_apply_auto_listing_type(listing, corpus, parsed)

    catalog_out = ensure_watch_catalog_for_listing(
        db,
        listing,
        parsed,
        edit,
        entity_reason_codes=entity_res.reason_codes,
    )
    wm: WatchModel | None = None
    if listing.watch_model_id is not None:
        wm = db.get(WatchModel, listing.watch_model_id)

    score = compute_opportunity_score(
        listing,
        signals,
        parsed,
        repair_supplement=edit.repair_supplement if edit else None,
        donor_cost=edit.donor_cost if edit else None,
        watch_model=wm,
        settings=get_settings(),
    )
    if score:
        db.add(
            OpportunityScore(
                listing_id=listing.id,
                estimated_resale=score.estimated_resale,
                estimated_repair_cost=score.estimated_repair_cost,
                advised_max_buy=score.advised_max_buy,
                potential_profit=score.potential_profit,
                confidence=score.confidence,
                risk=score.risk,
                explanations=score.explanations,
            )
        )

    if listing.watch_model_id:
        refresh_watch_model_observed_bounds(db, listing.watch_model_id)
        enrich_watch_model_image_from_listing(db, listing, get_settings())
        maybe_refresh_market_snapshots_for_model(db, listing.watch_model_id, get_settings())
    return catalog_out
