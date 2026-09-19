"""StoryTrace V2 Scoring & Metrics Engine.

Evaluates raw V2 experiment outputs against data/eval/gold_dataset_v3.json (989 gold verified conflicts).

Calculates:
  - Micro and Macro Precision, Recall, F1 for:
      * Primary Tier (verified_hard_conflict only)
      * Full Calibrated (verified_hard_conflict + verified_narrative_anomaly)
      * Raw Candidate Detector (before investigation filtering)
  - Addressable Recall (over 812 V2-addressable gold items) vs Global Recall (over 989 total gold)
  - Category-level metrics (possession, location, injury, clothing_appearance, other)
  - Rule-level candidate metrics across the 8 SQL analytical window rules
  - Agent investigation metrics: FP suppression rate, precision lift, tool call efficiency
  - Writes output to data/eval/v2/v2_experiment_scored_metrics.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("score_v2_experiment")

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = REPO_ROOT / "data" / "eval" / "gold_dataset_v3.json"
V2_RAW_PATH = REPO_ROOT / "data" / "eval" / "v2" / "v2_experiment_raw_results.json"
V2_SCORED_PATH = REPO_ROOT / "data" / "eval" / "v2" / "v2_experiment_scored_metrics.json"


def load_gold_dataset() -> Dict[str, Any]:
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_prf1(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
    return {
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def is_matching_finding(finding: Dict[str, Any], gold_item: Dict[str, Any]) -> bool:
    g_entity = str(gold_item.get("entity", "")).lower()
    g_attr = str(gold_item.get("attribute", "")).lower()
    g_desc = str(gold_item.get("description", "")).lower()

    f_entity = str(finding.get("entity_id", "") or "").lower()
    if not f_entity and finding.get("entity_ids"):
        f_entity = " ".join([str(e).lower() for e in finding["entity_ids"]])
    
    f_attr = str(finding.get("attribute", "")).lower()
    f_desc = str(finding.get("description", "") or finding.get("explanation", "")).lower()

    entity_match = g_entity in f_entity or f_entity in g_entity or any(w in f_entity for w in g_entity.split() if len(w) > 3)
    attr_match = (
        g_attr in f_attr or f_attr in g_attr
        or g_attr in f_desc or f_attr in g_desc
        or ("location" in g_attr and "spatial" in f_attr)
        or ("possession" in g_attr and "possession" in f_attr)
        or ("clothing" in g_attr and "clothing" in f_attr)
        or ("injury" in g_attr and "physical" in f_attr)
    )
    return entity_match and attr_match


def score_finding_set(findings: List[Dict[str, Any]], gold_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    tp = 0
    matched_gold_ids = set()

    for f in findings:
        for g_idx, g in enumerate(gold_items):
            if g_idx not in matched_gold_ids and is_matching_finding(f, g):
                tp += 1
                matched_gold_ids.add(g_idx)
                break

    fp = len(findings) - tp
    fn = len(gold_items) - len(matched_gold_ids)

    res = calculate_prf1(tp, fp, fn)
    res["surfaced_count"] = len(findings)
    res["gold_count"] = len(gold_items)
    res["matched_gold_indices"] = list(matched_gold_ids)
    return res


def score_v2(raw_results: Dict[str, Any], gold_data: Dict[str, Any]) -> Dict[str, Any]:
    films_gold = gold_data.get("films", {})

    per_film_metrics = {}
    aggregate_raw_candidates = {"tp": 0, "fp": 0, "fn": 0, "surfaced": 0, "gold": 0}
    aggregate_hard_only = {"tp": 0, "fp": 0, "fn": 0, "surfaced": 0, "gold": 0}
    aggregate_full_v2 = {"tp": 0, "fp": 0, "fn": 0, "surfaced": 0, "gold": 0}

    total_tool_calls = 0
    total_candidates = 0
    total_suppressed_by_agent = 0

    category_counts_v2 = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "gold": 0})
    rule_counts_v2 = defaultdict(lambda: {"tp": 0, "fp": 0, "candidates": 0})

    for film_slug, film_data in raw_results.items():
        film_gold_all = films_gold.get(film_slug, [])
        film_gold_verified = [
            g for g in film_gold_all
            if g.get("verdict_status") == "verified" or g.get("consensus_verdict") == "verified"
        ]

        candidates = film_data.get("candidates", [])
        findings = film_data.get("findings", [])
        tool_calls = film_data.get("total_tool_calls", 0)
        total_tool_calls += tool_calls
        total_candidates += len(candidates)

        hard_findings = [f for f in findings if f.get("status") == "verified_hard_conflict"]
        full_findings = [
            f for f in findings
            if f.get("status") in ("verified_hard_conflict", "verified_narrative_anomaly")
        ]

        suppressed = len(candidates) - len(full_findings)
        total_suppressed_by_agent += suppressed

        score_candidates = score_finding_set(candidates, film_gold_verified)
        score_hard = score_finding_set(hard_findings, film_gold_verified)
        score_full = score_finding_set(full_findings, film_gold_verified)

        per_film_metrics[film_slug] = {
            "gold_count": len(film_gold_verified),
            "candidates_count": len(candidates),
            "surfaced_hard_count": len(hard_findings),
            "surfaced_full_count": len(full_findings),
            "tool_calls": tool_calls,
            "raw_candidate_metrics": score_candidates,
            "hard_conflict_metrics": score_hard,
            "full_calibrated_metrics": score_full,
        }

        # Aggregate counts
        for k in ("tp", "fp", "fn", "surfaced", "gold"):
            aggregate_raw_candidates[k] += score_candidates.get(k, 0)
            aggregate_hard_only[k] += score_hard.get(k, 0)
            aggregate_full_v2[k] += score_full.get(k, 0)

        # Rule counts
        for cand in candidates:
            r = cand.get("rule_type", "unknown")
            rule_counts_v2[r]["candidates"] += 1

        for f in full_findings:
            r = f.get("rule_type", "unknown")
            # check if TP
            is_tp = any(is_matching_finding(f, g) for g in film_gold_verified)
            if is_tp:
                rule_counts_v2[r]["tp"] += 1
            else:
                rule_counts_v2[r]["fp"] += 1

        # Category counts
        for g in film_gold_verified:
            cat = g.get("conflict_type", g.get("attribute", "other")).lower()
            category_counts_v2[cat]["gold"] += 1

        for f in full_findings:
            cat = f.get("attribute", "other").lower()
            if "location" in cat or "spatial" in cat:
                c_key = "location"
            elif "possession" in cat:
                c_key = "possession"
            elif "injury" in cat or "physical" in cat:
                c_key = "injury"
            elif "clothing" in cat:
                c_key = "clothing_appearance"
            else:
                c_key = "other"

            is_tp = any(is_matching_finding(f, g) for g in film_gold_verified)
            if is_tp:
                category_counts_v2[c_key]["tp"] += 1
            else:
                category_counts_v2[c_key]["fp"] += 1

    # Macro averages across films
    macro_p_full = sum(m["full_calibrated_metrics"]["precision"] for m in per_film_metrics.values()) / len(per_film_metrics) if per_film_metrics else 0.0
    macro_r_full = sum(m["full_calibrated_metrics"]["recall"] for m in per_film_metrics.values()) / len(per_film_metrics) if per_film_metrics else 0.0
    macro_f1_full = sum(m["full_calibrated_metrics"]["f1"] for m in per_film_metrics.values()) / len(per_film_metrics) if per_film_metrics else 0.0

    micro_full = calculate_prf1(aggregate_full_v2["tp"], aggregate_full_v2["fp"], aggregate_full_v2["fn"])
    micro_hard = calculate_prf1(aggregate_hard_only["tp"], aggregate_hard_only["fp"], aggregate_hard_only["fn"])
    micro_cand = calculate_prf1(aggregate_raw_candidates["tp"], aggregate_raw_candidates["fp"], aggregate_raw_candidates["fn"])

    # Addressable Recall (Denominator = 812 addressable gold items)
    addressable_gold_total = 812
    addressable_recall_full = round(aggregate_full_v2["tp"] / addressable_gold_total, 4)
    addressable_recall_candidates = round(aggregate_raw_candidates["tp"] / addressable_gold_total, 4)

    scored_summary = {
        "dataset": "StoryTrace Gold Dataset v3 (989 Verified Ground Truth)",
        "total_gold_verified": 989,
        "v2_addressable_gold": 812,
        "evaluated_films_count": len(per_film_metrics),
        "overall_metrics": {
            "v2_full_calibrated": {
                "micro": micro_full,
                "macro": {
                    "precision": round(macro_p_full, 4),
                    "recall": round(macro_r_full, 4),
                    "f1": round(macro_f1_full, 4),
                },
                "addressable_recall": addressable_recall_full,
            },
            "v2_hard_conflict_only": {
                "micro": micro_hard,
            },
            "v2_raw_candidates_detector": {
                "micro": micro_cand,
                "addressable_recall": addressable_recall_candidates,
            }
        },
        "agent_efficiency": {
            "total_candidates_evaluated": total_candidates,
            "total_suppressed_by_agent": total_suppressed_by_agent,
            "suppression_rate": round(total_suppressed_by_agent / total_candidates, 4) if total_candidates > 0 else 0.0,
            "total_tool_calls": total_tool_calls,
            "avg_tool_calls_per_candidate": round(total_tool_calls / total_candidates, 2) if total_candidates > 0 else 0.0,
            "precision_gain_from_agent": round(micro_full["precision"] - micro_cand["precision"], 4),
        },
        "per_category_metrics": {k: dict(v) for k, v in category_counts_v2.items()},
        "per_rule_metrics": {k: dict(v) for k, v in rule_counts_v2.items()},
        "per_film_metrics": per_film_metrics,
    }

    return scored_summary


def main():
    if not V2_RAW_PATH.exists():
        logger.error(f"V2 raw results not found at {V2_RAW_PATH}. Please run scripts.v2.run_v2_eval first.")
        return

    gold_data = load_gold_dataset()
    with open(V2_RAW_PATH, "r", encoding="utf-8") as f:
        raw_results = json.load(f)

    scored_summary = score_v2(raw_results, gold_data)

    V2_SCORED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(V2_SCORED_PATH, "w", encoding="utf-8") as f:
        json.dump(scored_summary, f, indent=2)

    logger.info(f"=== StoryTrace V2 Scoring Complete. Scored metrics written to {V2_SCORED_PATH} ===")
    logger.info(f"Full V2 Micro-F1: {scored_summary['overall_metrics']['v2_full_calibrated']['micro']['f1']}")
    logger.info(f"Full V2 Addressable Recall: {scored_summary['overall_metrics']['v2_full_calibrated']['addressable_recall']}")
    logger.info(f"Agent Suppression Rate: {scored_summary['agent_efficiency']['suppression_rate']}")


if __name__ == "__main__":
    main()
