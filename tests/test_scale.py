import pytest

from google_trends_compare.scale import batch_keywords, rescale_batches


def test_batches_hold_at_most_five_terms_and_always_the_anchor():
    groups = batch_keywords([f"k{i}" for i in range(10)], anchor="k0")
    assert all(len(g) <= 5 and g[0] == "k0" for g in groups)
    assert sorted({k for g in groups for k in g}) == sorted(f"k{i}" for i in range(10))


def test_a_term_measured_in_two_batches_lands_on_the_same_value():
    # Batch 2 was rescaled by Google so its own peak is 100: every value is doubled.
    b1 = {"anchor": [40.0, 50.0], "a": [20.0, 30.0], "witness": [10.0, 10.0]}
    b2 = {"anchor": [80.0, 100.0], "b": [40.0, 20.0], "witness": [20.0, 20.0]}
    first = {r.keyword: r for r in rescale_batches([b1], "anchor")}
    second = {r.keyword: r for r in rescale_batches([b2, b1], "anchor")}
    assert first["witness"].average / first["anchor"].average == pytest.approx(
        second["witness"].average / second["anchor"].average
    )


def test_common_scale_peaks_at_100_and_ranks_by_average():
    b1 = {"anchor": [50.0, 100.0], "a": [10.0, 20.0]}
    b2 = {"anchor": [25.0, 50.0], "b": [100.0, 100.0]}
    results = {r.keyword: r for r in rescale_batches([b1, b2], "anchor")}
    assert max(max(r.series) for r in results.values()) == 100
    assert results["b"].rank == 1
    assert sum(r.share_of_total_pct for r in results.values()) == pytest.approx(100, abs=0.05)


def test_a_term_too_small_is_flagged_not_reported_as_zero():
    b1 = {"anchor": [100.0, 90.0], "tiny": [0.0, 0.0]}
    tiny = next(r for r in rescale_batches([b1], "anchor") if r.keyword == "tiny")
    assert not tiny.measurable
    assert tiny.rank is None and tiny.share_of_total_pct is None
    assert tiny.notes


def test_an_anchor_without_signal_is_refused():
    with pytest.raises(ValueError):
        rescale_batches([{"anchor": [0.0, 0.0], "a": [10.0, 20.0]}], "anchor")
