"""Computes precision/recall/F1 for all 4 ablation conditions from the
human-annotated data/eval/annotation_template.csv, plus entity-type
breakdown, cost efficiency, and an example-level paired bootstrap
significance test (Condition A vs Condition D).

Does NOT duplicate scripts/eval/engine.py's compute_metrics() -- that
function scores Condition A alone against data/eval/golden_dataset.py's
fixed golden set (used by run_eval.py's continuous regression check). This
script scores ALL FOUR conditions against the human-annotated CSV, which is
a different data source and a different comparison this repo did not have
before. Per the approved plan (item A1), true negatives are NOT counted
globally -- TP/FP/FN are computed only over the candidate population each
condition's detector/baseline actually surfaced, plus explicit
false_negative rows a human annotator added for conflicts the system missed.
"resolution_precision" (correctly-resolved / total-resolved) stands in for
agent discrimination instead of a global specificity claim.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_CSV = REPO_ROOT / "data" / "eval" / "annotation_template.csv"
METRICS_DIR = REPO_ROOT / "data" / "eval" / "metrics"
ABLATION_DIR = REPO_ROOT / "data" / "eval" / "ablation"


def _load_annotations() -> list[dict]:
    if not ANNOTATION_CSV.exists():
        print(f"{ANNOTATION_CSV} does not exist -- run build_annotation_template.py and complete GOLD_LABEL first.", file=sys.stderr)
        sys.exit(1)
    with open(ANNOTATION_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    unlabeled = [r for r in rows if not r.get("GOLD_LABEL", "").strip()]
    if unlabeled:
        print(
            f"WARNING: {len(unlabeled)}/{len(rows)} rows have no GOLD_LABEL -- "
            "these are excluded from all metrics below until annotated.",
            file=sys.stderr,
        )
    return [r for r in rows if r.get("GOLD_LABEL", "").strip()]


def _prf1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def compute_condition_metrics(rows: list[dict]) -> dict:
    """rows: annotation_template.csv rows for ONE condition (system_verdict
    already reflects what that condition produced). GOLD_LABEL values:
    true_positive / false_positive / false_negative."""
    tp = sum(1 for r in rows if r["GOLD_LABEL"] == "true_positive")
    fp = sum(1 for r in rows if r["GOLD_LABEL"] == "false_positive")
    fn = sum(1 for r in rows if r["GOLD_LABEL"] == "false_negative")
    metrics = _prf1(tp, fp, fn)

    resolved_rows = [r for r in rows if r["system_verdict"] == "resolved"]
    resolved_correct = sum(1 for r in resolved_rows if r["GOLD_LABEL"] == "true_negative")
    metrics["resolution_precision"] = (
        resolved_correct / len(resolved_rows) if resolved_rows else None
    )
    total_candidates = sum(1 for r in rows if r["system_verdict"] in ("verified", "resolved", "uncertain"))
    metrics["fp_suppression_rate"] = (
        resolved_correct / total_candidates if total_candidates else None
    )
    return metrics


def entity_type_breakdown(rows: list[dict]) -> dict:
    """Condition A only, broken down by attribute category prefix."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        attr = r.get("attribute", "")
        category = attr.split(".")[0] if "." in attr else attr
        buckets[category].append(r)
    return {cat: compute_condition_metrics(bucket_rows) for cat, bucket_rows in buckets.items()}


def cost_summary_for_condition(condition: str) -> dict:
    files = sorted(ABLATION_DIR.glob(f"*_condition_{condition}.json"))
    if not files:
        return {"avg_api_calls": None, "avg_cost_usd": None, "films": 0}
    calls, costs = [], []
    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        calls.append(data.get("api_calls_total", 0))
        costs.append(data.get("estimated_cost_usd", 0.0))
    return {
        "avg_api_calls": sum(calls) / len(calls),
        "avg_cost_usd": sum(costs) / len(costs),
        "films": len(files),
    }


def _gold_conflict_key(row: dict) -> tuple:
    """Identifies the same underlying real-world continuity conflict across
    conditions, since each condition's own conflict_id is internal to that
    condition's run (Condition D's one-shot findings have no conflict_id at
    all) and cannot be used to align rows_a/rows_d by list position. Keys on
    the gold-conflict identity fields instead: same film, same attribute,
    same approximate scene pair -- these describe the same real conflict
    regardless of which system found it.
    """
    return (row.get("film_slug", ""), row.get("attribute", ""), row.get("prior_scene", ""), row.get("current_scene", ""))


def paired_bootstrap_significance(
    rows_a: list[dict], rows_d: list[dict], n_resamples: int = 10000, seed: int = 0
) -> dict:
    """Example-level bootstrap on F1, per plan item A4 -- resamples
    individual annotated conflicts (pooled across all films), NOT the 10
    per-film F1 numbers, since 10 points is too small a sample to bootstrap
    informatively.

    True pairing (same resampled index draws the "same" underlying conflict
    for both conditions) requires rows_a and rows_d to actually reference the
    same real-world conflicts -- joined here via _gold_conflict_key, NOT via
    raw list position, since each condition's own conflict_id space differs
    (Condition D's baseline findings have no conflict_id at all). Only the
    intersection of keys present in both conditions is used for the paired
    part of the comparison; rows unique to one condition are reported
    separately rather than silently mispaired against an unrelated row.
    """
    if not rows_a or not rows_d:
        return {"comparison": "Condition A vs Condition D", "test": "paired bootstrap", "p_value": None, "significant": False, "note": "insufficient data"}

    keys_a = {_gold_conflict_key(r): r for r in rows_a}
    keys_d = {_gold_conflict_key(r): r for r in rows_d}
    shared_keys = sorted(set(keys_a) & set(keys_d))

    observed_f1_a = compute_condition_metrics(rows_a)["f1"]
    observed_f1_d = compute_condition_metrics(rows_d)["f1"]

    if len(shared_keys) < 2:
        return {
            "comparison": "Condition A vs Condition D",
            "test": "paired bootstrap (example-level) -- SKIPPED: too few shared gold-conflict keys to pair",
            "observed_f1_a": observed_f1_a,
            "observed_f1_d": observed_f1_d,
            "n_rows_a": len(rows_a),
            "n_rows_d": len(rows_d),
            "n_shared_keys": len(shared_keys),
            "p_value": None,
            "significant": False,
        }

    rng = random.Random(seed)
    n = len(shared_keys)
    paired_a = [keys_a[k] for k in shared_keys]
    paired_d = [keys_d[k] for k in shared_keys]
    observed_diff = compute_condition_metrics(paired_a)["f1"] - compute_condition_metrics(paired_d)["f1"]

    count_le_zero = 0
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        sample_a = [paired_a[i] for i in idx]
        sample_d = [paired_d[i] for i in idx]
        diff = compute_condition_metrics(sample_a)["f1"] - compute_condition_metrics(sample_d)["f1"]
        if diff <= 0:
            count_le_zero += 1

    p_value = count_le_zero / n_resamples
    return {
        "comparison": "Condition A vs Condition D",
        "test": "paired bootstrap (example-level, joined on film/attribute/scene-pair, n_resamples=%d)" % n_resamples,
        "observed_f1_a_overall": observed_f1_a,
        "observed_f1_d_overall": observed_f1_d,
        "observed_f1_a_paired_subset": compute_condition_metrics(paired_a)["f1"],
        "observed_f1_d_paired_subset": compute_condition_metrics(paired_d)["f1"],
        "observed_diff": observed_diff,
        "n_examples_paired": n,
        "n_rows_a_total": len(rows_a),
        "n_rows_d_total": len(rows_d),
        "p_value": p_value,
        "significant": p_value < 0.05,
    }


def main() -> None:
    rows = _load_annotations()
    by_condition: dict[str, list[dict]] = defaultdict(list)
    # annotation_template.csv as built by build_annotation_template.py only
    # covers Condition A -- rows for B/C/D must be added the same way (a
    # separate build_annotation_template.py run pointed at each condition's
    # ablation JSON, or a `condition` column added manually) before this
    # aggregates across all four. This script computes what's present and
    # reports which conditions are missing rather than silently proceeding.
    for r in rows:
        condition = r.get("condition", "A")  # defaults to A for the current single-condition template
        by_condition[condition].append(r)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    aggregate = {}
    for condition, condition_rows in sorted(by_condition.items()):
        metrics = compute_condition_metrics(condition_rows)
        cost = cost_summary_for_condition(condition)
        aggregate[f"condition_{condition}"] = {**metrics, **cost}
        for film_slug in {r["film_slug"] for r in condition_rows}:
            film_rows = [r for r in condition_rows if r["film_slug"] == film_slug]
            out_path = METRICS_DIR / f"condition_{condition}_{film_slug}.json"
            out_path.write_text(json.dumps(compute_condition_metrics(film_rows), indent=2), encoding="utf-8")

    if "A" in by_condition:
        breakdown = entity_type_breakdown(by_condition["A"])
        (METRICS_DIR / "entity_type_breakdown.json").write_text(json.dumps(breakdown, indent=2), encoding="utf-8")

    if "A" in by_condition and "D" in by_condition:
        aggregate["statistical_test"] = paired_bootstrap_significance(by_condition["A"], by_condition["D"])
    else:
        aggregate["statistical_test"] = {"note": "Condition A and/or D rows missing from annotation_template.csv -- cannot compute yet."}

    (METRICS_DIR / "aggregate.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    missing = {"A", "B", "C", "D"} - set(by_condition)
    print(f"Wrote metrics for conditions: {sorted(by_condition)} -> {METRICS_DIR}")
    if missing:
        print(f"WARNING: no annotated rows found for condition(s) {sorted(missing)} yet.", file=sys.stderr)


if __name__ == "__main__":
    main()
