from __future__ import annotations
from typing import Dict, List, Set, Tuple
import math

def compute_revision_metrics(
    predictions: List[Dict[Tuple[str, str], str]],
    ground_truths: List[Dict[Tuple[str, str], str]]
) -> Dict[str, float]:
    """Computes Revision Precision, Revision Recall, Preservation Accuracy, and Delta Exact Match."""
    total_rev_pred = 0
    correct_rev_pred = 0
    total_rev_gold = 0
    correct_rev_gold = 0

    total_keep_gold = 0
    correct_keep_pred = 0

    unsupported_revisions = 0
    total_claims = 0

    exact_matches = 0

    for pred, gold in zip(predictions, ground_truths):
        all_keys = set(pred.keys()).union(set(gold.keys()))
        is_exact = True

        for k in all_keys:
            p_val = pred.get(k, "KEEP")
            g_val = gold.get(k, "KEEP")
            total_claims += 1

            if p_val != g_val:
                is_exact = False

            # Revision metrics
            if p_val in ("REVISE", "CONFLICT", "INVALIDATE"):
                total_rev_pred += 1
                if p_val == g_val:
                    correct_rev_pred += 1
                elif g_val == "KEEP":
                    unsupported_revisions += 1

            if g_val in ("REVISE", "CONFLICT", "INVALIDATE"):
                total_rev_gold += 1
                if p_val == g_val:
                    correct_rev_gold += 1

            # Preservation metrics
            if g_val == "KEEP":
                total_keep_gold += 1
                if p_val == "KEEP":
                    correct_keep_pred += 1

        if is_exact:
            exact_matches += 1

    rev_precision = (correct_rev_pred / total_rev_pred) if total_rev_pred > 0 else 1.0
    rev_recall = (correct_rev_gold / total_rev_gold) if total_rev_gold > 0 else 1.0
    preservation_acc = (correct_keep_pred / total_keep_gold) if total_keep_gold > 0 else 1.0
    unsupported_rate = (unsupported_revisions / total_rev_pred) if total_rev_pred > 0 else 0.0
    exact_match_rate = (exact_matches / len(predictions)) if len(predictions) > 0 else 0.0

    rev_f1 = (2 * rev_precision * rev_recall / (rev_precision + rev_recall)) if (rev_precision + rev_recall) > 0 else 0.0

    return {
        "revision_precision": rev_precision,
        "revision_recall": rev_recall,
        "revision_f1": rev_f1,
        "preservation_accuracy": preservation_acc,
        "unsupported_revision_rate": unsupported_rate,
        "delta_exact_match": exact_match_rate
    }
