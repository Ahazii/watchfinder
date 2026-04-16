"""Small numeric helpers (no DB imports)."""

from __future__ import annotations

from decimal import Decimal


def percentile_sorted(sorted_vals: list[Decimal], p: float) -> Decimal | None:
    """Linear interpolation percentile on a sorted non-empty list, p in [0, 1]."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    if lo == hi:
        return sorted_vals[lo]
    frac = Decimal(str(idx - lo))
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac
