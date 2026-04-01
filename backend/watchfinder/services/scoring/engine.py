"""Opportunity score from listing + repair signals + parsed hints."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from watchfinder.services.repair.extract import SignalHit
from watchfinder.services.scoring import constants as C

if TYPE_CHECKING:
    from watchfinder.models import Listing


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
) -> ScoreResult | None:
    """
    If no repair signals, returns None (caller clears stale scores).
    """
    if not signals:
        return None

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

    if list_price > 0:
        estimated_resale = (list_price * mult).quantize(Decimal("0.01"))
        explanations.append(
            f"Estimated resale: list price {list_price} × {mult} = {estimated_resale} (heuristic, not appraisal)."
        )
    else:
        estimated_resale = None
        explanations.append(
            "No list price; resale estimate skipped (cannot anchor multiplier)."
        )

    advised_max_buy = None
    potential_profit = None
    if estimated_resale is not None:
        advised_max_buy = estimated_resale - estimated_repair - C.DESIRED_MARGIN
        potential_profit = estimated_resale - estimated_repair - list_price
        explanations.append(
            f"Advised max buy (before fees): resale {estimated_resale} − total repair {estimated_repair} − margin {C.DESIRED_MARGIN} = {advised_max_buy}"
        )
        explanations.append(
            f"Potential profit if bought at list ({list_price}): {potential_profit}"
        )

    conf = C.CONFIDENCE_BASE + C.CONFIDENCE_PER_SIGNAL * len(signals)
    conf = min(C.CONFIDENCE_MAX, conf)
    explanations.append(
        f"Confidence {conf}: based on {len(signals)} distinct signal(s) (rule of thumb)."
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
