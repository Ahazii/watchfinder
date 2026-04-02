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
)
from watchfinder.services.parsing import build_listing_corpus, parse_watch_attributes
from watchfinder.services.repair import extract_repair_signals
from watchfinder.services.scoring import compute_opportunity_score
from watchfinder.services.watch_models import (
    refresh_watch_model_observed_bounds,
    try_auto_link_listing,
)


def analyze_listing(db: Session, listing: Listing) -> None:
    corpus = build_listing_corpus(listing)
    parsed = parse_watch_attributes(listing.title, corpus)
    signals = extract_repair_signals(corpus)

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

    edit = db.get(ListingEdit, listing.id)
    score = compute_opportunity_score(
        listing,
        signals,
        parsed,
        repair_supplement=edit.repair_supplement if edit else None,
        donor_cost=edit.donor_cost if edit else None,
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

    try_auto_link_listing(db, listing, parsed, edit)
    if listing.watch_model_id:
        refresh_watch_model_observed_bounds(db, listing.watch_model_id)
