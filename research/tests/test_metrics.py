import numpy as np
import pytest
from research.ssr_bench.metrics import KEYS, item_counts, per_story, summarize
from research.ssr_bench import stats


def task(claims):
    return {"claims": [{"id": f"c{i}", "attr": a, "entity": e, "slot": 3, "value": "x", "statement": ""} for i, (a, e) in enumerate(claims)]}


def gold(labels, bounded=False):
    return {"labels": {f"c{i}": {"label": l, "value": v} for i, (l, v) in enumerate(labels)}, "meta": {"scope_bounded": bounded}, "story_id": "s"}


def pred(*ps):
    return {f"c{i}": p for i, p in enumerate(ps)}


T = task([("loc", "A"), ("proploc", "k"), ("loc", "B"), ("injured", "B")])
G = gold([("REVISE", "tower"), ("REVISE", "tower"), ("KEEP", ""), ("CONFLICT", "")])
K = ("KEEP", "")


def S(p, g=G, t=T):
    return summarize(item_counts(t, g, p))


def test_perfect():
    s = S(pred(("REVISE", "tower"), ("REVISE", "tower"), K, ("CONFLICT", "")))
    assert s["revision_precision"] == s["revision_recall"] == s["preservation_accuracy"] == s["delta_exact_match"] == 1
    assert s["conflict_recall"] == 1 and s["collateral_claim_rate"] == 0 and s["unsupported_item_rate"] == 0


def test_always_keep_games_preservation_but_not_recall():
    s = S(pred(K, K, K, K))
    assert s["preservation_accuracy"] == 1.0 and s["revision_recall"] == 0.0 and s["delta_exact_match"] == 0
    assert s["revision_precision"] is None            # undefined, not 1.0
    assert s["conflict_recall"] == 0.0


def test_revise_everything_games_recall_but_not_preservation():
    s = S(pred(*[("REVISE", "tower")] * 4))
    assert s["revision_recall"] == 1.0 and s["preservation_accuracy"] == 0.0
    assert s["collateral_claim_rate"] == 1.0 and s["revision_precision"] == 2 / 4


def test_wrong_value_with_right_label_is_wrong():
    s = S(pred(("REVISE", "cellar"), ("REVISE", "tower"), K, ("CONFLICT", "")))
    assert s["revision_recall"] == 0.5 and s["revision_precision"] == 0.5 and s["delta_exact_match"] == 0


def test_invalid_is_not_preservation_but_not_collateral():
    s = S(pred(("REVISE", "tower"), ("REVISE", "tower"), ("INVALID", ""), ("CONFLICT", "")))
    assert s["preservation_accuracy"] == 0.0 and s["collateral_claim_rate"] == 0.0 and s["invalid_rate"] == 0.25


def test_item_level_and_claim_level_unsupported_rates_differ():
    t2 = task([("loc", "A")] * 10)
    g2 = gold([("KEEP", "")] * 10)
    p = pred(*([("REVISE", "q")] + [K] * 9))
    s = S(p, g2, t2)
    assert s["collateral_claim_rate"] == 0.1 and s["unsupported_item_rate"] == 1.0


def test_dependent_recall_and_temporal_scope():
    g = gold([("REVISE", "tower"), ("REVISE", "tower"), ("KEEP", ""), ("CONFLICT", "")], bounded=True)
    t = task([("loc", "A"), ("proploc", "k"), ("loc", "B"), ("injured", "B")])
    s = S(pred(("REVISE", "tower"), K, K, ("CONFLICT", "")), g, t)
    assert s["dependent_recall"] == 0.0
    assert s["temporal_scope_acc"] == 0.5          # claims on groups (loc,A) and (proploc,k): one right, one missed


def test_missing_prediction_counts_as_invalid_not_keep():
    s = S({"c0": ("REVISE", "tower")})
    assert s["invalid_rate"] == 0.75 and s["preservation_accuracy"] == 0.0


def test_story_clusters_sum_to_total():
    cs = {"i1": item_counts(T, G, pred(K, K, K, K)), "i2": item_counts(T, G, pred(("REVISE", "tower"), ("REVISE", "tower"), K, ("CONFLICT", "")))}
    gb = {"i1": {"story_id": "a"}, "i2": {"story_id": "a"}}
    sids, M = per_story(cs, gb)
    assert sids == ["a"] and np.allclose(M[0], sum(cs.values()))


def test_bootstrap_ci_contains_estimate_and_paired_test_detects_big_effect():
    rng = np.random.default_rng(0)
    A = np.zeros((40, len(KEYS)))
    Bm = np.zeros_like(A)
    for M, rate in ((A, 0.9), (Bm, 0.3)):
        M[:, KEYS.index("items")] = 3
        M[:, KEYS.index("exact_items")] = rng.binomial(3, rate, 40)
    est, lo, hi = stats.boot_ci(A, "delta_exact_match", b=500)
    assert lo <= est <= hi
    d = stats.paired_diff(A, Bm, "delta_exact_match", b=500)
    assert d["diff"] > 0.4 and d["p_perm"] < 0.01 and d["ci_lo"] > 0
    null = stats.paired_diff(A, A.copy(), "delta_exact_match", b=500)
    assert null["diff"] == 0 and null["p_perm"] > 0.5


def test_holm_is_monotone_and_conservative():
    h = stats.holm({"a": 0.01, "b": 0.02, "c": 0.5})
    assert h["a"] == pytest.approx(0.03) and h["b"] == pytest.approx(0.04) and h["c"] == pytest.approx(0.5)
