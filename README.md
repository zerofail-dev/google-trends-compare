# google-trends-compare

Compare **any number of Google Trends keywords on one common 0-100 scale**, in plain Python.

The Google Trends API endpoint this library calls compares at most 5 terms per request (a 6th
term is refused with HTTP 400; the website itself may show more), and it rescales every request so
that its own peak is 100. Two requests are therefore **not comparable**:
a 50 in one batch is not a 50 in the next. This library fixes that with an **anchor term**: the
same keyword is included in every batch, and each batch is rescaled by the anchor's values.

```bash
pip install git+https://github.com/zerofail-dev/google-trends-compare
python -m google_trends_compare notion jira asana trello clickup basecamp wrike airtable --geo US
```

The output is one table: every keyword with its rank, its average interest on the common scale,
and its share of the total.

## How it works

1. Pick an anchor (by default the first keyword).
2. Split the other keywords into batches of 4, and add the anchor to each batch: 5 terms per
   request, the most Google accepts.
3. Fetch each batch. Each comes back on its own 0-100 scale.
4. Rescale every batch by `mean(anchor in the first batch) / mean(anchor in this batch)`.
5. Renormalize so the highest point of all keywords is 100, then rank by average.

The arithmetic is in [`google_trends_compare/scale.py`](google_trends_compare/scale.py), with no
network access, and tested in [`tests/test_scale.py`](tests/test_scale.py). It works on series from
any source, not only this library's client.

## Use it from Python

```python
from google_trends_compare import compare

for r in compare(["notion", "jira", "asana", "trello", "clickup", "wrike"], geo="US"):
    print(r.rank, r.keyword, r.average, r.share_of_total_pct, r.measurable)
```

Already have the batches (from pytrends, a CSV export, anything)? Use only the arithmetic:

```python
from google_trends_compare import rescale_batches

results = rescale_batches([batch1, batch2], anchor="notion")  # each batch: {keyword: [values]}
```

## Three pitfalls

- **Choose a mid-sized anchor.** Google returns integers. Next to a huge anchor, a small keyword is
  rounded to 0 in its batch, and no rescaling can bring it back. Such keywords are **flagged as not
  measurable** (`measurable=False`, no rank, no share). They are never reported as 0, because 0 here
  means "too small to measure", not "no interest".
- **The anchor must have signal in every batch.** An anchor at 0 cannot rescale anything, so the
  library refuses it with a `ValueError` instead of returning nonsense.
- **Google rate-limits these endpoints (HTTP 429).** The client retries once, then stops with a
  clear error. It never returns an empty series as if it were data. A blocked IP can stay blocked
  for over an hour, so space your runs.

## Limits

- It uses the internal endpoints of the Google Trends website. They are undocumented and can
  change without notice.
- It uses one fixed anchor. Chaining through intermediate anchors (to rescue very small terms),
  retries across sessions, interest by region and related queries are out of scope here.
- Interest is **relative** (0-100), not a number of searches.

## Hosted version

Disclosure: I also maintain a hosted version on Apify,
[Google Trends Scraper & API: Compare 100 Keywords](https://apify.com/zerofail/google-trends-scraper).
It adds adaptive anchors and chaining, rate-limit handling, interest by region, related queries, a
daily "changes only" mode, and calls from n8n, Make, Clay or AI agents (MCP). You do not need it:
the code above works on its own.

## License

MIT. See [LICENSE](LICENSE).
