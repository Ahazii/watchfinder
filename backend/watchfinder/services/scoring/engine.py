"""Opportunity score from listing + repair signals + parsed hints."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from watchfinder.config import Settings, get_settings
from watchfinder.services.repair.extract import SignalHit
from watchfinder.services.scoring import constants as C
from watchfinder.services.scoring.catalog_anchor import working_resale_anchor_gbp
from watchfinder.services.scoring.listing_gbp import listing_ask_gbp

if TYPE_CHECKING:
    from watchfinder.models import Listing, WatchModel


@dataclass
class ScoreResult:
    estimated_resale: Decimal | None
    estimated_repair_cost: Decimal | None
    advised_max_buy: Decimal | None
    potential_profit: Decimal | None
    confidence: Decimal | None
    risk: Decimal | None
    explanations: list[str]
    is_candidate: bool


def _dominant_category(signals: list[SignalHit]) -> str:
    if not signals:
        return "none"
    by_weight = max(signals, key=lambda s: s.weight)
    return by_weight.signal_type


def compute_opportunity_score(
    listing: Listing,
    signals: list[SignalHit],
    parsed: dict[str, str],
    *,
    repair_supplement: Decimal | None = None,
    donor_cost: Decimal | None = None,
    watch_model: WatchModel | None = None,
    settings: Settings | None = None,
) -> ScoreResult | None:
    """
    If no repair signals, returns None (caller clears stale scores).

    When the listing is linked to a **watch_models** row with manual or observed
    £ bounds, estimates resale from that **working-market anchor** (converted back
    to the listing currency for storage/display). Otherwise keeps the list-price
    × multiplier heuristic.
    """
    if not signals:
        return None

    settings = settings or get_settings()
    explanations: list[str] = []
    list_price = listing.current_price or Decimal("0")

    for s in signals:
        explanations.append(
            f"Matched “{s.matched_text}” → {s.signal_type} (weight {s.weight:.2f})"
        )

    if parsed.get("brand"):
        explanations.append(f"Parsed brand: {parsed['brand']}")
    if parsed.get("reference"):
        explanations.append(f"Parsed reference hint: {parsed['reference']}")
    if parsed.get("caliber"):
        explanations.append(f"Parsed caliber hint: {parsed['caliber']}")
    if parsed.get("running_state"):
        explanations.append(f"Running state hint: {parsed['running_state']}")

    total_weight = sum(s.weight for s in signals)
    rule_repair = C.BASE_REPAIR + (
        Decimal(str(total_weight)) * C.REPAIR_PER_WEIGHT_UNIT
    )
    sup = repair_supplement if repair_supplement is not None else Decimal("0")
    donor = donor_cost if donor_cost is not None else Decimal("0")
    estimated_repair = rule_repair + sup + donor
    explanations.append(
        f"Repair (rule core): {rule_repair} (base {C.BASE_REPAIR} + weight×{C.REPAIR_PER_WEIGHT_UNIT})"
    )
    if sup > 0:
        explanations.append(f"Repair add-on (manual/historical): +{sup}")
    if donor > 0:
        explanations.append(f"Donor / parts acquisition allowance: +{donor}")
    explanations.append(f"Estimated repair (total): {estimated_repair}")

    cat = _dominant_category(signals)
    if cat in ("parts_only", "parts_repair"):
        mult = C.RESALE_MULTIPLIER_PARTS
        explanations.append("Resale multiplier: parts-lot scenario (conservative).")
    elif cat in ("needs_repair", "needs_service", "non_runner", "non_functional"):
        mult = C.RESALE_MULTIPLIER_REPAIR
        explanations.append("Resale multiplier: repair project scenario.")
    else:
        mult = C.RESALE_MULTIPLIER_DEFAULT
        explanations.append("Resale multiplier: default uplift scenario.")

    target_gbp, basis = (None, "")
    if watch_model is not None:
        target_gbp, basis = working_resale_anchor_gbp(watch_model)
        if target_gbp is not None:
            explanations.append(
                f"Catalog link: {watch_model.brand} "
                f"{watch_model.reference or watch_model.model_family or ''}".strip()
            )

    ask_gbp: Decimal | None = None
    ask_note = ""
    if list_price > 0:
        ask_gbp, ask_note = listing_ask_gbp(list_price, listing.currency, settings)

    used_catalog = False
    target_use_gbp: Decimal | None = None
    estimated_resale: Decimal | None = None
    gbp_per_unit: Decimal | None = None
    if list_price > 0 and ask_gbp is not None:
        gbp_per_unit = (ask_gbp / list_price).quantize(Decimal("0.0000001"))

    if target_gbp is not None and ask_gbp is not None and gbp_per_unit and gbp_per_unit > 0:
        if cat in ("parts_only", "parts_repair"):
            target_use_gbp = (target_gbp * Decimal("0.55")).quantize(Decimal("0.01"))
            explanations.append(
                f"Working-market anchor ({basis}): £{target_gbp} → parts bundle target ×0.55 = £{target_use_gbp}"
            )
        else:
            target_use_gbp = target_gbp
            explanations.append(f"Working-market anchor ({basis}): £{target_use_gbp}")

        explanations.append(ask_note)
        estimated_resale = (target_use_gbp / gbp_per_unit).quantize(Decimal("0.01"))
        explanations.append(
            f"Estimated resale (listing currency): £{target_use_gbp} → {estimated_resale} "
            f"(same scale as asking price; not a professional appraisal)."
        )
        used_catalog = True
    elif list_price > 0:
        estimated_resale = (list_price * mult).quantize(Decimal("0.01"))
        if target_gbp is not None and ask_gbp is None:
            explanations.append(
                f"Catalog £ anchor available (£{target_gbp}) but {ask_note}; using list × {mult} heuristic instead."
            )
        elif watch_model and target_gbp is None:
            explanations.append(
                "Listing linked to watch catalog row but no manual/observed £ bounds yet — using list × multiplier."
            )
        else:
            explanations.append(
                f"Estimated resale: list price {list_price} × {mult} = {estimated_resale} (heuristic, not appraisal)."
            )
    else:
        estimated_resale = None
        explanations.append(
            "No list price; resale estimate skipped (cannot anchor)."
        )

    advised_max_buy = None
    potential_profit = None
    if estimated_resale is not None:
        if used_catalog and target_use_gbp is not None and ask_gbp is not None and gbp_per_unit and gbp_per_unit > 0:
            profit_gbp = target_use_gbp - estimated_repair - ask_gbp
            margin_gbp = C.DESIRED_MARGIN
            max_buy_gbp = target_use_gbp - estimated_repair - margin_gbp
            potential_profit = (profit_gbp / gbp_per_unit).quantize(Decimal("0.01"))
            advised_max_buy = (max_buy_gbp / gbp_per_unit).quantize(Decimal("0.01"))
            explanations.append(
                f"Advised max buy (before fees): (£{target_use_gbp} − £{estimated_repair} − margin £{margin_gbp}) "
                f"→ {advised_max_buy} in listing currency"
            )
            explanations.append(
                f"Potential profit if bought at list: (£{profit_gbp} GBP after repair & ask) "
                f"→ {potential_profit} (listing currency)"
            )
        else:
            advised_max_buy = estimated_resale - estimated_repair - C.DESIRED_MARGIN
            potential_profit = estimated_resale - estimated_repair - list_price
            explanations.append(
                f"Advised max buy (before fees): resale {estimated_resale} − total repair {estimated_repair} "
                f"− margin {C.DESIRED_MARGIN} = {advised_max_buy}"
            )
            explanations.append(
                f"Potential profit if bought at list ({list_price}): {potential_profit}"
            )

    conf = C.CONFIDENCE_BASE + C.CONFIDENCE_PER_SIGNAL * len(signals)
    if used_catalog:
        conf += Decimal("0.08")
    conf = min(C.CONFIDENCE_MAX, conf)
    explanations.append(
        f"Confidence {conf}: based on {len(signals)} signal(s)"
        + (" + catalog anchor" if used_catalog else "")
        + " (rule of thumb).",
    )

    risk = Decimal("0.35")
    types = {s.signal_type for s in signals}
    if "untested" in types:
        risk += C.RISK_UNTESTED_BUMP
        explanations.append("Risk +untested: outcome less certain.")
    if "water_damage" in types or "corrosion" in types:
        risk += C.RISK_WATER_BUMP
        explanations.append("Risk +water/corrosion: may need movement overhaul.")
    risk = min(C.RISK_MAX, risk)
    explanations.append(f"Risk score {risk} (0=low, 1=high), rule-based.")

    return ScoreResult(
        estimated_resale=estimated_resale,
        estimated_repair_cost=estimated_repair,
        advised_max_buy=advised_max_buy,
        potential_profit=potential_profit,
        confidence=conf,
        risk=risk,
        explanations=explanations,
        is_candidate=potential_profit is not None and potential_profit > 0,
    )
