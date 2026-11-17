"""Minimal Google Trends client: interest over time for up to 5 terms per request.

It calls the same internal endpoints the Google Trends website uses (``explore`` for the widget
token, then ``widgetdata/multiline`` for the series). These endpoints are undocumented and can
change, and Google rate-limits them (HTTP 429). This client retries once and then raises: it
never returns an empty series as if it were data.
"""

from __future__ import annotations

import json
import time
import urllib.parse

from curl_cffi import requests

BASE = "https://trends.google.com/trends/api"


class TrendsError(RuntimeError):
    """Google refused or answered something that is not data."""


class TrendsClient:
    def __init__(self, hl: str = "en-US", tz: int = 0, pause: float = 1.0, retry_wait: float = 5.0):
        self.session = requests.Session(impersonate="chrome")
        self.hl, self.tz, self.pause, self.retry_wait = hl, tz, pause, retry_wait

    def _get(self, path: str, params: dict) -> dict:
        url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
        for attempt in (1, 2):
            response = self.session.get(url, timeout=30)
            time.sleep(self.pause)
            if response.status_code == 200 and response.text.startswith(")]}'"):
                return json.loads(response.text[response.text.index("\n") + 1 :])
            if response.status_code != 429 or attempt == 2:
                raise TrendsError(f"{path}: HTTP {response.status_code}")
            time.sleep(self.retry_wait)
        raise TrendsError(f"{path}: no answer")  # unreachable, keeps type checkers happy

    def interest_over_time(
        self, keywords: list[str], timeframe: str = "today 12-m", geo: str = ""
    ) -> tuple[list[str], dict[str, list[float]]]:
        """Return (dates, {keyword: values}) for at most 5 keywords on one 0-100 scale."""
        if not 1 <= len(keywords) <= 5:
            raise ValueError("the explore endpoint accepts 1 to 5 terms per request")
        req = {
            "comparisonItem": [{"keyword": k, "geo": geo, "time": timeframe} for k in keywords],
            "category": 0,
            "property": "",
        }
        common = {"hl": self.hl, "tz": str(self.tz)}
        explore = self._get("explore", {**common, "req": json.dumps(req, separators=(",", ":"))})
        widget = next((w for w in explore.get("widgets", []) if w.get("id") == "TIMESERIES"), None)
        if widget is None:
            raise TrendsError("explore: no TIMESERIES widget")
        data = self._get(
            "widgetdata/multiline",
            {
                **common,
                "req": json.dumps(widget["request"], separators=(",", ":")),
                "token": widget["token"],
            },
        )
        points = data.get("default", {}).get("timelineData", [])
        if not points:
            raise TrendsError("multiline: empty timeline")
        dates = [p.get("formattedAxisTime", p.get("time", "")) for p in points]
        series = {k: [float(p["value"][i]) for p in points] for i, k in enumerate(keywords)}
        return dates, series
