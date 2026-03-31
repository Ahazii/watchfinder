"""Scan corpus for repair / defect phrases; return signal records (not ORM yet)."""

from __future__ import annotations

from dataclasses import dataclass

from watchfinder.services.parsing.keywords import repair_phrases_sorted


@dataclass
class SignalHit:
    signal_type: str
    matched_text: str
    source_field: str
    weight: float


def _overlaps(used: list[tuple[int, int]], a: int, b: int) -> bool:
    for lo, hi in used:
        if not (b <= lo or a >= hi):
            return True
    return False


def extract_repair_signals(corpus: str, *, source_field: str = "corpus") -> list[SignalHit]:
    if not corpus:
        return []
    lower = corpus.lower()
    hits: list[SignalHit] = []
    used: list[tuple[int, int]] = []

    for phrase, signal_type, weight in repair_phrases_sorted():
        start = 0
        while True:
            idx = lower.find(phrase, start)
            if idx == -1:
                break
            end = idx + len(phrase)
            if _overlaps(used, idx, end):
                start = idx + 1
                continue
            raw = corpus[idx:end]
            hits.append(
                SignalHit(
                    signal_type=signal_type,
                    matched_text=raw[:512],
                    source_field=source_field,
                    weight=weight,
                )
            )
            used.append((idx, end))
            start = end

    return hits
