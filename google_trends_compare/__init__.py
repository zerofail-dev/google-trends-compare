"""Compare any number of Google Trends keywords on one common 0-100 scale."""

from __future__ import annotations

from .client import TrendsClient, TrendsError
from .scale import KeywordResult, batch_keywords, rescale_batches

__all__ = ["KeywordResult", "TrendsClient", "TrendsError", "batch_keywords", "compare", "rescale_batches"]


def compare(
    keywords: list[str],
    anchor: str | None = None,
    timeframe: str = "today 12-m",
    geo: str = "",
    client: TrendsClient | None = None,
) -> list[KeywordResult]:
    """Fetch every keyword in batches of 5 sharing one anchor, and return them on one scale.

    The anchor defaults to the first keyword. Pick a mid-sized term: next to a very big anchor,
    small keywords are rounded to 0 by Google and come back flagged as not measurable.
    """
    anchor = anchor or keywords[0]
    client = client or TrendsClient()
    batches = []
    for group in batch_keywords(keywords, anchor):
        _, series = client.interest_over_time(group, timeframe=timeframe, geo=geo)
        batches.append(series)
    return rescale_batches(batches, anchor)
