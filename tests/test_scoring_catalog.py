"""Catalog anchor and listing→GBP helpers for repair opportunity scoring."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from watchfinder.services.scoring.catalog_anchor import working_resale_anchor_gbp
from watchfinder.services.scoring.engine import compute_opportunity_score
from watchfinder.services.scoring.listing_gbp import listing_ask_gbp


def test_working_anchor_prefers_manual_midpoint() -> None:
    wm = SimpleNamespace(
        manual_price_low=Decimal("1000"),
        manual_price_high=Decimal("3000"),
        observed_price_low=Decimal("100"),
        observed_price_high=Decimal("200"),
    )
    val, basis = working_resale_anchor_gbp(wm)
    assert val == Decimal("2000.00")
    assert "manual" in basis


def test_working_anchor_observed_when_no_manual() -> None:
    wm = SimpleNamespace(
        manual_price_low=None,
        manual_price_high=None,
        observed_price_low=Decimal("400"),
        observed_price_high=Decimal("600"),
    )
    val, basis = working_resale_anchor_gbp(wm)
    assert val == Decimal("500.00")
    assert "observed" in basis


def test_listing_ask_gbp_gbp_identity() -> None:
    gbp, note = listing_ask_gbp(Decimal("500"), "GBP", settings=MagicMock())
    assert gbp == Decimal("500.00")
    assert "500" in note


def test_compute_opportunity_uses_catalog_when_linked() -> None:
    listing = MagicMock()
    listing.current_price = Decimal("100")
    listing.currency = "GBP"

    wm = SimpleNamespace(
        brand="X",
        reference="123",
        model_family=None,
        manual_price_low=Decimal("900"),
        manual_price_high=Decimal("1100"),
        observed_price_low=None,
        observed_price_high=None,
    )

    sig = MagicMock()
    sig.matched_text = "spares"
    sig.signal_type = "needs_repair"
    sig.weight = 0.5

    r = compute_opportunity_score(
        listing,
        [sig],
        {"brand": "X"},
        watch_model=wm,
        settings=MagicMock(),
    )
    assert r is not None
    assert r.estimated_resale is not None
    # Midpoint £1000, repair > 0, ask £100 → positive profit
    assert r.potential_profit is not None
    assert r.potential_profit > 0
    assert any("Working-market anchor" in x for x in (r.explanations or []))


def test_compute_opportunity_parts_discount() -> None:
    listing = MagicMock()
    listing.current_price = Decimal("50")
    listing.currency = "GBP"

    wm = SimpleNamespace(
        brand="X",
        reference=None,
        model_family=None,
        manual_price_high=Decimal("1000"),
        manual_price_low=Decimal("1000"),
        observed_price_low=None,
        observed_price_high=None,
    )

    sig = MagicMock()
    sig.matched_text = "parts"
    sig.signal_type = "parts_only"
    sig.weight = 0.5

    r = compute_opportunity_score(listing, [sig], {"brand": "X"}, watch_model=wm, settings=MagicMock())
    assert r is not None
    assert r.estimated_resale is not None
    assert any("×0.55" in x or "0.55" in x for x in (r.explanations or []))
