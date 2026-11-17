"""Command line: python -m google_trends_compare notion jira asana trello clickup --geo US"""

from __future__ import annotations

import argparse
import csv
import sys

from . import TrendsError, compare


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Google Trends keywords on one scale.")
    parser.add_argument("keywords", nargs="+")
    parser.add_argument("--anchor", help="term present in every request (default: first keyword)")
    parser.add_argument("--timeframe", default="today 12-m")
    parser.add_argument("--geo", default="", help="country code, e.g. US (default: worldwide)")
    parser.add_argument("--csv", help="also write the full series to this CSV file")
    args = parser.parse_args()

    try:
        results = compare(args.keywords, anchor=args.anchor, timeframe=args.timeframe, geo=args.geo)
    except TrendsError as exc:
        print(f"Google Trends refused the request ({exc}).", file=sys.stderr)
        if "429" in str(exc):
            print(
                "HTTP 429 means this IP is rate-limited. The block usually lifts after about an hour; "
                "make fewer requests per run, or run from another network.",
                file=sys.stderr,
            )
        return 1
    print(f"{'rank':>4}  {'keyword':<24} {'average':>8} {'share %':>8}  note")
    for r in results:
        rank = str(r.rank) if r.rank else "-"
        share = f"{r.share_of_total_pct:.2f}" if r.share_of_total_pct is not None else "-"
        note = "" if r.measurable else "too small to measure"
        print(f"{rank:>4}  {r.keyword:<24} {r.average:>8.2f} {share:>8}  {note}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["keyword", "rank", "average", "share_of_total_pct", "measurable", "series"])
            for r in results:
                writer.writerow([r.keyword, r.rank, r.average, r.share_of_total_pct, r.measurable, r.series])
    return 0


if __name__ == "__main__":
    sys.exit(main())
