from __future__ import annotations

from decimal import Decimal

from watchfinder.numeric_stats import percentile_sorted


def test_percentile_median_three():
    xs = [Decimal("10"), Decimal("20"), Decimal("30")]
    assert percentile_sorted(xs, 0.5) == Decimal("20")


def test_percentile_endpoints():
    xs = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4")]
    assert percentile_sorted(xs, 0.25) == Decimal("1.75")
    assert percentile_sorted(xs, 0.75) == Decimal("3.25")
