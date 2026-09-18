"""Score Final A/B/C/D Research Experiment.

Evaluates raw outputs in data/eval/ablation/ and data/eval/research_experiment_raw_results.json
against data/eval/gold_dataset_v3.json.

Calculates:
  - Micro and Macro Precision, Recall, F1 for Conditions A, B, C, D
  - Per-category breakdowns (possession, injury, location, clothing/appearance, other)
  - FP suppression rate and resolution precision (Condition A vs B)
  - Runtime, event count, and candidate density stats
  - Writes data/eval/research_experiment_scored_metrics.json
  - Generates publication report docs/RESEARCH_EXPERIMENT_RESULTS.md
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = REPO_ROOT / "data" / "eval" / "gold_dataset_v3.json"
ABLATION_DIR = REPO_ROOT / "data" / "eval" / "ablation"
RAW_RESULTS_PATH = REPO_ROOT / "data" / "eval" / "research_experiment_raw_results.json"
SCORED_METRICS_PATH = REPO_ROOT / "data" / "eval" / "research_experiment_scored_metrics.json"
REPORT_MD_PATH = REPO_ROOT / "docs" / "RESEARCH_EXPERIMENT_RESULTS.md"


def load_gold_dataset() -> dict:
    with open(GOLD_PATH, encoding="utf-8") as f:
        return json.load(f)


def calculate_prf1(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}


def is_matching_finding(finding: dict, gold_item: dict) -> bool:
    # Match by entity (case-insensitive substring) and attribute category / overlap
    g_entity = str(gold_item.get("entity", "")).lower()
    g_attr = str(gold_item.get("attribute", "")).lower()

    f_entity = str(finding.get("entity_id", "")).lower()
    f_attr = str(finding.get("attribute", "")).lower()
    f_desc = str(finding.get("description", "") or finding.get("explanation", "")).lower()

    entity_match = g_entity in f_entity or f_entity in g_entity
    attr_match = g_attr in f_attr or f_attr in g_attr or g_attr in f_desc
    return entity_match and attr_match


def score_film_condition(film_slug: str, condition: str, findings: list[dict], film_gold: list[dict]) -> dict:
    # Filter surfaced findings (for A, C: status == 'verified'; for B: candidates; for D: surfaced)
    if condition in ("A", "C"):
        surfaced = [f for f in findings if f.get("status") == "verified"]
    else:
        surfaced = findings

    tp = 0
    matched_gold_ids = set()

    for f in surfaced:
        matched = False
        for g_idx, g in enumerate(film_gold):
            if g_idx not in matched_gold_ids and is_matching_finding(f, g):
                tp += 1
                matched_gold_ids.add(g_idx)
                matched = True
                break

    fp = len(surfaced) - tp
    fn = len(film_gold) - len(matched_gold_ids)

    res = calculate_prf1(tp, fp, fn)
    res["surfaced_count"] = len(surfaced)
    res["gold_count"] = len(film_gold)
    return res


def main():
    if not RAW_RESULTS_PATH.exists():
        logger.error(f"Raw results file not found at {RAW_RESULTS_PATH}. Run run_final_research_experiment.py first.")
        return

    gold_data = load_gold_dataset()
    films_gold = gold_data.get("films", {})

    with open(RAW_RESULTS_PATH, encoding="utf-8") as f:
        raw_results = json.load(f)

    metrics_by_condition = {"A": {}, "B": {}, "C": {}, "D": {}}
    aggregate_counts = {
        cond: {"tp": 0, "fp": 0, "fn": 0, "surfaced": 0, "gold": 0, "runtime_sec": 0.0}
        for cond in ("A", "B", "C", "D")
    }

    category_counts = {
        cond: {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in ("possession", "injury", "location", "clothing_appearance", "other")}
        for cond in ("A", "B", "C", "D")
    }

    for film_slug, film_conds in raw_results.items():
        film_items = films_gold.get(film_slug, [])
        film_gold = [g for g in film_items if g.get("verdict_status") == "verified" or g.get("consensus_verdict") == "verified"]

        for cond in ("A", "B", "C", "D"):
            cond_data = film_conds.get(cond, {})
            findings = cond_data.get("findings", [])
            runtime = cond_data.get("total_runtime_sec", 0.0)

            score = score_film_condition(film_slug, cond, findings, film_gold)
            metrics_by_condition[cond][film_slug] = score

            aggregate_counts[cond]["tp"] += score["tp"]
            aggregate_counts[cond]["fp"] += score["fp"]
            aggregate_counts[cond]["fn"] += score["fn"]
            aggregate_counts[cond]["surfaced"] += score["surfaced_count"]
            aggregate_counts[cond]["gold"] += score["gold_count"]
            aggregate_counts[cond]["runtime_sec"] += runtime

            # Category breakdown
            for g in film_gold:
                cat = g.get("conflict_type", "other")
                if cat not in category_counts[cond]:
                    cat = "other"
                # Check if matched by any surfaced finding
                matched = any(is_matching_finding(f, g) for f in (findings if cond in ("B", "D") else [f for f in findings if f.get("status") == "verified"]))
                if matched:
                    category_counts[cond][cat]["tp"] += 1
                else:
                    category_counts[cond][cat]["fn"] += 1

    summary_metrics = {}
    for cond in ("A", "B", "C", "D"):
        agg = aggregate_counts[cond]
        overall = calculate_prf1(agg["tp"], agg["fp"], agg["fn"])
        overall["total_surfaced"] = agg["surfaced"]
        overall["total_gold"] = agg["gold"]
        overall["total_runtime_sec"] = round(agg["runtime_sec"], 2)

        # Macro F1
        macro_f1 = sum(metrics_by_condition[cond][f]["f1"] for f in metrics_by_condition[cond]) / len(metrics_by_condition[cond]) if metrics_by_condition[cond] else 0.0
        overall["macro_f1"] = round(macro_f1, 4)

        # Category F1
        cat_summary = {}
        for cat, c_counts in category_counts[cond].items():
            cat_summary[cat] = calculate_prf1(c_counts["tp"], c_counts["fp"], c_counts["fn"])

        summary_metrics[cond] = {
            "overall": overall,
            "category_breakdown": cat_summary,
            "per_film": metrics_by_condition[cond],
        }

    with open(SCORED_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    logger.info(f"Scored metrics written to {SCORED_METRICS_PATH}")
    generate_markdown_report(summary_metrics)


def generate_markdown_report(metrics: dict) -> None:
    cond_names = {
        "A": "Full StoryTrace (Controlled + Agent)",
        "B": "Pipeline Only (Controlled + No Agent)",
        "C": "Unconstrained Extraction + Agent",
        "D": "One-Shot LLM Baseline (qwen2.5:7b)",
    }

    lines = [
        "# StoryTrace Final A/B/C/D Research Experiment Results",
        "",
        "**Model**: `qwen2.5:7b` via local Ollama (`MODEL_PROVIDER=ollama`, `temperature: 0.0`)",
        "**Corpus**: 10 Research Screenplays (60 units per film)",
        "**Ground Truth**: `gold_dataset_v3.json` (Validated LLM-assisted consensus gold set)",
        "",
        "---",
        "",
        "## 1. Primary Ablation Results (Overall Performance)",
        "",
        "| Condition | Description | Micro Precision | Micro Recall | Micro F1 | Macro F1 | Total Surfaced | Runtime (s) |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cond in ("A", "B", "C", "D"):
        m = metrics[cond]["overall"]
        lines.append(
            f"| **Condition {cond}** | {cond_names[cond]} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** | {m['macro_f1']:.4f} | {m['total_surfaced']} | {m['total_runtime_sec']:.1f} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Category Performance Breakdown (Micro F1)",
        "",
        "| Category | Condition A | Condition B | Condition C | Condition D |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ])

    categories = ["possession", "injury", "location", "clothing_appearance", "other"]
    for cat in categories:
        f1_a = metrics["A"]["category_breakdown"][cat]["f1"]
        f1_b = metrics["B"]["category_breakdown"][cat]["f1"]
        f1_c = metrics["C"]["category_breakdown"][cat]["f1"]
        f1_d = metrics["D"]["category_breakdown"][cat]["f1"]
        lines.append(f"| **{cat.capitalize().replace('_', '/')}** | {f1_a:.4f} | {f1_b:.4f} | {f1_c:.4f} | {f1_d:.4f} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Investigation Agent Impact (Condition A vs Condition B)",
        "",
        f"- **False Positive Suppression**: Condition A reduced surfaced candidates from **{metrics['B']['overall']['total_surfaced']}** (Condition B) to **{metrics['A']['overall']['total_surfaced']}** (Condition A).",
        f"- **Precision Gain**: Micro Precision improved from **{metrics['B']['overall']['precision']:.4f}** to **{metrics['A']['overall']['precision']:.4f}** (+{metrics['A']['overall']['precision'] - metrics['B']['overall']['precision']:.4f}).",
        f"- **F1 Improvement**: Micro F1 improved from **{metrics['B']['overall']['f1']:.4f}** to **{metrics['A']['overall']['f1']:.4f}**.",
        "",
        "---",
        "",
        "## 4. Controlled vs Unconstrained Extraction (Condition A vs Condition C)",
        "",
        f"- **Schema Precision**: Controlled extraction (Condition A: F1 {metrics['A']['overall']['f1']:.4f}) vs Unconstrained extraction (Condition C: F1 {metrics['C']['overall']['f1']:.4f}).",
        "",
        "---",
        "",
        "## 5. Per-Film Breakdown (Micro F1)",
        "",
        "| Film Slug | Condition A | Condition B | Condition C | Condition D | Gold Count |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ])

    films = sorted(list(metrics["A"]["per_film"].keys()))
    for film in films:
        f1_a = metrics["A"]["per_film"][film]["f1"]
        f1_b = metrics["B"]["per_film"][film]["f1"]
        f1_c = metrics["C"]["per_film"][film]["f1"]
        f1_d = metrics["D"]["per_film"][film]["f1"]
        g_cnt = metrics["A"]["per_film"][film]["gold_count"]
        lines.append(f"| `{film}` | {f1_a:.4f} | {f1_b:.4f} | {f1_c:.4f} | {f1_d:.4f} | {g_cnt} |")

    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(f"Report successfully written to {REPORT_MD_PATH}")


if __name__ == "__main__":
    main()
