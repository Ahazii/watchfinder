"""Tunable scoring economics (rules-first; replace with data-driven later)."""

from decimal import Decimal

# Fixed GBP-style margin you want on a flip (currency-agnostic number)
DESIRED_MARGIN = Decimal("75")

# Base repair £ when any signal fires
BASE_REPAIR = Decimal("40")

# Per-signal add-on scaled by weight
REPAIR_PER_WEIGHT_UNIT = Decimal("120")

# Resale uplift multipliers by dominant signal category
RESALE_MULTIPLIER_PARTS = Decimal("1.15")
RESALE_MULTIPLIER_REPAIR = Decimal("1.25")
RESALE_MULTIPLIER_DEFAULT = Decimal("1.20")

# Confidence caps
CONFIDENCE_PER_SIGNAL = Decimal("0.12")
CONFIDENCE_BASE = Decimal("0.25")
CONFIDENCE_MAX = Decimal("0.95")

# Risk base + bumps
RISK_UNTESTED_BUMP = Decimal("0.12")
RISK_WATER_BUMP = Decimal("0.15")
RISK_MAX = Decimal("0.95")
