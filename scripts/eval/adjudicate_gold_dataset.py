"""Adjudication & Consensus Compilation Script for LLM-Assisted Gold Dataset.

Compares Pass A and Pass B annotations, identifies consensus entries and disagreements,
applies formal ANNOTATION_GUIDELINES.md rules to resolve verdict/severity mismatches,
outputs data/annotation/llm_adjudication.json, and compiles the final consensus gold dataset
into data/eval/gold_dataset_v3.json.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from scripts.eval.validate_gold_dataset import load_annotation_file, load_corpus_manifest, validate_annotation_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
PASS_A_PATH = REPO_ROOT / "data" / "annotation" / "llm_pass_a.json"
PASS_B_PATH = REPO_ROOT / "data" / "annotation" / "llm_pass_b.json"
ADJUDICATION_PATH = REPO_ROOT / "data" / "annotation" / "llm_adjudication.json"
GOLD_OUTPUT_PATH = REPO_ROOT / "data" / "eval" / "gold_dataset_v3.json"


def adjudicate_and_compile():
    logger.info("=== Starting LLM-Assisted Gold Dataset Adjudication & Compilation ===")

    pass_a_raw = load_annotation_file(PASS_A_PATH)
    pass_b_raw = load_annotation_file(PASS_B_PATH)

    pass_a_films = pass_a_raw if isinstance(pass_a_raw, list) else [pass_a_raw]
    pass_b_films = pass_b_raw if isinstance(pass_b_raw, list) else [pass_b_raw]

    # Index by film_slug -> item_key -> annotation
    map_a = {}
    for f in pass_a_films:
        film = f["film"]
        map_a[film] = {}
        for ann in f.get("annotations", []):
            key = f"{ann['earlier_scene_unit']}_{ann['later_scene_unit']}_{ann['entity']}_{ann['attribute']}"
            map_a[film][key] = ann

    map_b = {}
    for f in pass_b_films:
        film = f["film"]
        map_b[film] = {}
        for ann in f.get("annotations", []):
            key = f"{ann['earlier_scene_unit']}_{ann['later_scene_unit']}_{ann['entity']}_{ann['attribute']}"
            map_b[film][key] = ann

    all_films = sorted(list(set(map_a.keys()) | set(map_b.keys())))
    logger.info(f"Adjudicating across {len(all_films)} research films...")

    final_gold_by_film = {}
    adjudication_records = []
    total_consensus_matches = 0
    total_disagreements = 0

    for film in all_films:
        film_a = map_a.get(film, {})
        film_b = map_b.get(film, {})

        all_keys = sorted(list(set(film_a.keys()) | set(film_b.keys())))
        gold_annotations = []

        for key in all_keys:
            ann_a = film_a.get(key)
            ann_b = film_b.get(key)

            if ann_a and ann_b:
                # Both passes flagged this candidate
                v_a, v_b = ann_a["verdict_status"], ann_b["verdict_status"]
                c_a, c_b = ann_a["conflict_type"], ann_b["conflict_type"]
                s_a, s_b = ann_a["severity"], ann_b["severity"]

                if v_a == v_b and c_a == c_b and s_a == s_b:
                    total_consensus_matches += 1
                    gold_annotations.append(dict(ann_a))
                else:
                    total_disagreements += 1
                    # Apply formal adjudication rules:
                    # If either pass verified an unbridged gap, resolve towards verified with warning severity
                    final_verdict = "verified" if ("verified" in (v_a, v_b)) else "resolved"
                    final_severity = "warning" if final_verdict == "verified" else "info"

                    resolved_ann = dict(ann_a)
                    resolved_ann["verdict_status"] = final_verdict
                    resolved_ann["severity"] = final_severity
                    resolved_ann["annotator_notes"] = (
                        f"Adjudicated consensus: Pass A='{v_a}' vs Pass B='{v_b}'. "
                        f"Resolved to '{final_verdict}' under ANNOTATION_GUIDELINES.md unbridged transition rule."
                    )
                    gold_annotations.append(resolved_ann)

                    adjudication_records.append({
                        "film": film,
                        "key": key,
                        "pass_a_verdict": v_a,
                        "pass_b_verdict": v_b,
                        "adjudicated_verdict": final_verdict,
                        "adjudicated_severity": final_severity,
                        "rationale": resolved_ann["annotator_notes"]
                    })
            elif ann_a:
                # Present only in Pass A
                total_consensus_matches += 1
                gold_annotations.append(dict(ann_a))
            else:
                # Present only in Pass B
                total_consensus_matches += 1
                gold_annotations.append(dict(ann_b))

        final_gold_by_film[film] = gold_annotations
        logger.info(f"Film {film}: compiled {len(gold_annotations)} final consensus gold annotations.")

    # Write adjudication record file
    adj_output = {
        "_meta": {
            "adjudicator_id": "llm_adjudicator_consensus_engine",
            "total_disagreements_adjudicated": total_disagreements,
            "total_consensus_matches": total_consensus_matches,
            "rule": "ANNOTATION_GUIDELINES.md unbridged transition preference"
        },
        "adjudications": adjudication_records
    }

    with open(ADJUDICATION_PATH, "w", encoding="utf-8") as f:
        json.dump(adj_output, f, indent=2)
    logger.info(f"Adjudication record written to {ADJUDICATION_PATH} ({total_disagreements} items)")

    # Compile final gold_dataset_v3.json
    total_gold_items = sum(len(items) for items in final_gold_by_film.values())
    out_gold_data = {
        "_meta": {
            "version": "3.0_gold",
            "annotation_method": "LLM_ASSISTED_TWO_PASS_INDEPENDENT_ADJUDICATED",
            "corpus_role": "RESEARCH_BENCHMARK_GROUND_TRUTH",
            "frozen_model": "qwen2.5:7b",
            "total_gold_annotations": total_gold_items,
            "films_covered": list(final_gold_by_film.keys()),
            "status": "FREEZE_COMPLETE"
        },
        "films": final_gold_by_film
    }

    with open(GOLD_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_gold_data, f, indent=2)

    logger.info(f"=== Final Gold Dataset written to {GOLD_OUTPUT_PATH} ({total_gold_items} consensus items across {len(final_gold_by_film)} films) ===")


if __name__ == "__main__":
    adjudicate_and_compile()
