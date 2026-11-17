"""Put Google Trends batches on one common scale.

The Google Trends API compares at most 5 terms per request and rescales every request so its own
peak is 100. Two requests are therefore not comparable. The fix is an anchor term present in every
batch: each batch is rescaled by the ratio between the anchor's values in a reference batch and
in that batch.

This module is pure arithmetic, with no network access, so it can be tested and reused with data
from any source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Below this average (on the 0-100 scale of its own batch), a term is too small for Google's
# integer rounding to measure it reliably against the anchor. It is flagged, never shown as 0.
DEFAULT_MIN_MEASURABLE = 1.0


@dataclass
class KeywordResult:
    """One keyword on the common scale."""

    keyword: str
    series: list[float]
    average: float
    peak: float
    measurable: bool
    rank: int | None = None
    share_of_total_pct: float | None = None
    notes: list[str] = field(default_factory=list)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def rescale_batches(
    batches: list[dict[str, list[float]]],
    anchor: str,
    min_measurable: float = DEFAULT_MIN_MEASURABLE,
) -> list[KeywordResult]:
    """Rescale several batches that all contain ``anchor`` onto the scale of the first batch.

    Each batch maps a keyword to its series (one value per date, same dates in every batch).
    The result is then renormalized so that the highest point of all keywords is 100.

    Raises ValueError when the anchor is missing from a batch or has no signal in it: rescaling
    by a zero anchor would turn every other term of that batch into nonsense.
    """
    if not batches:
        return []
    for i, batch in enumerate(batches):
        if anchor not in batch:
            raise ValueError(f"anchor {anchor!r} missing from batch {i}")
        if _mean(batch[anchor]) == 0:
            raise ValueError(f"anchor {anchor!r} has no signal in batch {i}; pick a bigger anchor")

    reference = _mean(batches[0][anchor])
    scaled: dict[str, list[float]] = {}
    raw_average: dict[str, float] = {}
    for batch in batches:
        factor = reference / _mean(batch[anchor])
        for keyword, series in batch.items():
            if keyword in scaled:
                continue  # the anchor (and any repeated term) keeps its first measurement
            scaled[keyword] = [v * factor for v in series]
            raw_average[keyword] = _mean(series)

    top = max((max(s) for s in scaled.values() if s), default=0.0)
    norm = 100.0 / top if top else 0.0

    results = []
    for keyword, series in scaled.items():
        values = [round(v * norm, 2) for v in series]
        measurable = raw_average[keyword] >= min_measurable
        result = KeywordResult(
            keyword=keyword,
            series=values,
            average=round(_mean(values), 2),
            peak=max(values) if values else 0.0,
            measurable=measurable,
        )
        if not measurable:
            result.notes.append(
                "too small to measure against the anchor (Google rounds to integers); "
                "do not read this as zero interest"
            )
        results.append(result)

    ranked = sorted((r for r in results if r.measurable), key=lambda r: r.average, reverse=True)
    total = sum(r.average for r in ranked)
    for position, r in enumerate(ranked, start=1):
        r.rank = position
        r.share_of_total_pct = round(r.average / total * 100, 2) if total else None
    return sorted(results, key=lambda r: (r.rank is None, r.rank or 0))


def batch_keywords(keywords: list[str], anchor: str, size: int = 5) -> list[list[str]]:
    """Split keywords into requests of at most ``size`` terms, each one including the anchor."""
    others = [k for k in dict.fromkeys(keywords) if k != anchor]
    per_batch = size - 1
    if not others:
        return [[anchor]]
    return [[anchor, *others[i : i + per_batch]] for i in range(0, len(others), per_batch)]
