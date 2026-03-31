"""
Tunable keyword dictionaries for repair detection and light watch parsing.
Edit lists here — no code changes needed for new phrases.
"""

from __future__ import annotations

# (lowercase phrase, signal_type, weight 0–1 for scoring severity)
REPAIR_PHRASES: list[tuple[str, str, float]] = [
    # strong defect / non-runner
    ("not working", "non_functional", 0.95),
    ("doesn't work", "non_functional", 0.95),
    ("does not work", "non_functional", 0.95),
    ("not running", "non_runner", 0.9),
    ("non running", "non_runner", 0.9),
    ("non-running", "non_runner", 0.9),
    ("won't run", "non_runner", 0.85),
    ("wont run", "non_runner", 0.85),
    ("stopped", "non_runner", 0.75),
    ("broken", "damage", 0.8),
    ("for parts", "parts_only", 0.85),
    ("for part", "parts_only", 0.75),
    ("parts only", "parts_only", 0.85),
    ("spares or repair", "parts_repair", 0.8),
    ("for repair", "needs_repair", 0.75),
    ("needs repair", "needs_repair", 0.75),
    ("needs service", "needs_service", 0.7),
    ("needs a service", "needs_service", 0.7),
    ("untested", "untested", 0.55),
    ("sold as untested", "untested", 0.6),
    ("runs briefly", "intermittent", 0.65),
    ("intermittent", "intermittent", 0.65),
    ("overwound", "mechanical_issue", 0.7),
    ("over wound", "mechanical_issue", 0.7),
    ("missing crown", "missing_part", 0.75),
    ("no crown", "missing_part", 0.7),
    ("missing stem", "missing_part", 0.75),
    ("cracked crystal", "crystal_damage", 0.65),
    ("water damage", "water_damage", 0.85),
    ("water damaged", "water_damage", 0.85),
    ("rust", "corrosion", 0.75),
    ("rusted", "corrosion", 0.75),
    ("dial damage", "dial_damage", 0.65),
    ("damaged dial", "dial_damage", 0.65),
    ("not keeping time", "accuracy", 0.55),
    ("losing time", "accuracy", 0.5),
]

# Longer phrases first for greedy matching (handled in extract)
def repair_phrases_sorted() -> list[tuple[str, str, float]]:
    return sorted(REPAIR_PHRASES, key=lambda x: len(x[0]), reverse=True)


# Brand tokens (title/corpus substring match, case-insensitive)
KNOWN_BRANDS: tuple[str, ...] = (
    "rolex",
    "omega",
    "tudor",
    "tag heuer",
    "breitling",
    "cartier",
    "iwc",
    "jaeger",
    "jlc",
    "longines",
    "tissot",
    "seiko",
    "citizen",
    "casio",
    "hamilton",
    "oris",
    "zenith",
    "patek",
    "audemars",
    "vacheron",
    "grand seiko",
    "nomos",
    "sinn",
    "damasko",
    "stowa",
    "junghans",
    "vostok",
    "timex",
    "bulova",
    "rado",
    "frederique constant",
    "raymond weil",
    "baume",
    "montblanc",
    "panerai",
    "hublot",
)

MOVEMENT_HINTS: tuple[str, ...] = (
    "automatic",
    "manual wind",
    "hand wind",
    "handwind",
    "quartz",
    "solar",
    "kinetic",
    "spring drive",
    "chronograph",
)
