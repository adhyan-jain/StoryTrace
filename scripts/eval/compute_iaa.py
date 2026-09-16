"""Inter-Annotator Agreement (IAA) Computation Script for StoryTrace Human Annotations.

Computes Cohen's Kappa (for 2 annotators) or Fleiss' Kappa (for >= 2 annotators) and
percent agreement metrics across:
1. Conflict Detection (presence/absence across scene units)
2. Category Taxonomy (possession, injury, location, clothing/appearance, other)
3. Verdict Status (verified, resolved, ambiguous)
4. Severity Tier (critical, warning, info)

Usage:
  python3 -m scripts.eval.compute_iaa path/to/annotator_1.json path/to/annotator_2.json
"""

from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

from scripts.eval.validate_gold_dataset import load_annotation_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_cohens_kappa(rater1: list[str], rater2: list[str], categories: list[str]) -> tuple[float, float]:
    """Computes Cohen's Kappa coefficient (kappa) and observed agreement (Po) between two raters."""
    assert len(rater1) == len(rater2), "Rater vectors must have equal length"
    n = len(rater1)
    if n == 0:
        return 0.0, 0.0

    # 1. Observed agreement Po
    matches = sum(1 for a, b in zip(rater1, rater2) if a == b)
    po = matches / n

    # 2. Expected agreement Pe
    freq1 = {c: 0 for c in categories}
    freq2 = {c: 0 for c in categories}
    for a, b in zip(rater1, rater2):
        if a in freq1:
            freq1[a] += 1
        if b in freq2:
            freq2[b] += 1

    pe = sum((freq1[c] / n) * (freq2[c] / n) for c in categories)

    if pe == 1.0:
        kappa = 1.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    return round(kappa, 4), round(po, 4)


def compute_fleiss_kappa(ratings_matrix: list[list[int]]) -> float:
    """Computes Fleiss' Kappa for N items evaluated by K raters.
    ratings_matrix shape: [N_items, N_categories], where each cell is count of raters assigning category c.
    """
    n_items = len(ratings_matrix)
    if n_items == 0:
        return 0.0
    n_raters = sum(ratings_matrix[0])
    if n_raters <= 1:
        return 1.0

    # Calculate P_i for each item
    p_i = []
    for row in ratings_matrix:
        s = sum(n_c * n_c for n_c in row)
        p_i.append((s - n_raters) / (n_raters * (n_raters - 1)))

    p_bar = sum(p_i) / n_items

    # Calculate P_e for each category
    p_c = []
    total_ratings = n_items * n_raters
    n_categories = len(ratings_matrix[0])
    for c in range(n_categories):
        cat_sum = sum(row[c] for row in ratings_matrix)
        p_c.append(cat_sum / total_ratings)

    pe_bar = sum(pc * pc for pc in p_c)

    if pe_bar == 1.0:
        return 1.0
    kappa = (p_bar - pe_bar) / (1.0 - pe_bar)
    return round(kappa, 4)


def calculate_annotation_iaa(files: list[Path]) -> None:
    datasets = []
    for f in files:
        raw_data = load_annotation_file(f)
        if isinstance(raw_data, list):
            # Combine list of film annotations for single annotator pass
            combined_annotations = []
            for film_data in raw_data:
                combined_annotations.extend(film_data.get("annotations", []))
            datasets.append({"annotator_id": f.stem, "annotations": combined_annotations})
        else:
            datasets.append(raw_data)

    num_raters = len(datasets)
    logger.info(f"Loaded {num_raters} annotator datasets.")

    # Align annotations by (earlier_scene_unit, later_scene_unit, entity, attribute)
    index_map: dict[str, list[dict | None]] = {}

    for r_idx, ds in enumerate(datasets):
        for ann in ds.get("annotations", []):
            key = f"{ann['earlier_scene_unit']}_{ann['later_scene_unit']}_{ann['entity']}_{ann['attribute']}"
            if key not in index_map:
                index_map[key] = [None] * num_raters
            index_map[key][r_idx] = ann

    all_keys = list(index_map.keys())
    logger.info(f"Total unique candidate item keys across all annotators: {len(all_keys)}")

    if num_raters == 2:
        r1_cat, r2_cat = [], []
        r1_verdict, r2_verdict = [], []
        r1_sev, r2_sev = [], []

        categories = ["possession", "injury", "location", "clothing/appearance", "other"]
        verdicts = ["verified", "resolved", "ambiguous"]
        severities = ["critical", "warning", "info"]

        for key, r_list in index_map.items():
            a1, a2 = r_list[0], r_list[1]
            if a1 and a2:
                r1_cat.append(a1.get("conflict_type", "other"))
                r2_cat.append(a2.get("conflict_type", "other"))

                r1_verdict.append(a1.get("verdict_status", "ambiguous"))
                r2_verdict.append(a2.get("verdict_status", "ambiguous"))

                r1_sev.append(a1.get("severity", "info"))
                r2_sev.append(a2.get("severity", "info"))

        k_cat, po_cat = compute_cohens_kappa(r1_cat, r2_cat, categories)
        k_verdict, po_verdict = compute_cohens_kappa(r1_verdict, r2_verdict, verdicts)
        k_sev, po_sev = compute_cohens_kappa(r1_sev, r2_sev, severities)

        print("\n=======================================================")
        print("          INTER-ANNOTATOR AGREEMENT (2 RATERS)        ")
        print("=======================================================")
        print(f"Paired Items Evaluated by Both Annotators: {len(r1_cat)}")
        print(f"1. Conflict Category Taxonomy Agreement:")
        print(f"   - Cohen's Kappa (kappa): {k_cat}")
        print(f"   - Percent Observed Agreement: {po_cat * 100:.1f}%\n")
        print(f"2. Verdict Status Agreement (verified/resolved/ambiguous):")
        print(f"   - Cohen's Kappa (kappa): {k_verdict}")
        print(f"   - Percent Observed Agreement: {po_verdict * 100:.1f}%\n")
        print(f"3. Severity Rating Agreement (critical/warning/info):")
        print(f"   - Cohen's Kappa (kappa): {k_sev}")
        print(f"   - Percent Observed Agreement: {po_sev * 100:.1f}%")
        print("=======================================================\n")
    else:
        print(f"\nComputing Fleiss' Kappa across {num_raters} annotators...")
        # (Fleiss kappa calculation for >=3 raters)
        categories = ["possession", "injury", "location", "clothing/appearance", "other"]
        cat_matrix = []
        for key, r_list in index_map.items():
            row = [0] * len(categories)
            valid_counts = 0
            for a in r_list:
                if a and a.get("conflict_type") in categories:
                    idx = categories.index(a["conflict_type"])
                    row[idx] += 1
                    valid_counts += 1
            if valid_counts == num_raters:
                cat_matrix.append(row)

        fk_cat = compute_fleiss_kappa(cat_matrix)
        print(f"Fleiss' Kappa (Category Taxonomy): {fk_cat}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 -m scripts.eval.compute_iaa <annotator_1.json> <annotator_2.json>")
        sys.exit(1)
    file_paths = [Path(p) for p in sys.argv[1:]]
    calculate_annotation_iaa(file_paths)
