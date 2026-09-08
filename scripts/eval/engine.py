"""Metrics dataclasses and matching logic for the preprocessing eval.

Pure comparison logic: no ClickHouse or pipeline imports. Callers (run_eval.py)
are responsible for turning raw ClickHouse rows into plain dicts with the key
names this module expects, so this file never needs to know about schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from data.eval.golden_dataset import GoldenConflict, GoldenStateEvent


@dataclass
class PhaseMetrics:
    phase: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    details: list[dict] = field(default_factory=list)  # per-item breakdown, see compute_metrics


@dataclass
class EvalReport:
    document: str
    timestamp: str
    extraction: PhaseMetrics
    detection: PhaseMetrics
    investigation: PhaseMetrics
    overall_f1: float
    notes: list[str] = field(default_factory=list)
    # seq_number -> {"extracted": int, "matched": int, "missed_attrs": list[str]}
    per_unit: dict[int, dict] = field(default_factory=dict)
    # {"baseline_f1": float, "engineered_f1": float, "units_tested": int} or None
    adversarial: dict | None = None


def match_state_event(
    predicted: dict,
    golden: GoldenStateEvent,
    tolerance_sequences: int = 1,
) -> bool:
    """`predicted` is a plain dict with keys: entity_name, entity_type,
    attribute, value, sequence_number, raw_excerpt (all produced by the
    caller from a joined ClickHouse row — entity_name/entity_type come from
    the `entities` table, not state_events itself).

    Matches if ALL of:
      - entity_name matches case-insensitively
      - attribute matches exactly (case-sensitive — these are controlled
        dotted paths like "possession.gun", not free text)
      - value matches exactly after lowercasing both sides
      - abs(predicted sequence_number - golden.sequence_number) <= tolerance_sequences
      - golden.excerpt_contains appears in predicted raw_excerpt, case-insensitive substring
    """
    if predicted.get("entity_name", "").strip().lower() != golden.entity_name.strip().lower():
        return False
    if predicted.get("attribute", "") != golden.attribute:
        return False
    if predicted.get("value", "").strip().lower() != golden.value.strip().lower():
        return False
    try:
        seq = int(predicted.get("sequence_number"))
    except (TypeError, ValueError):
        return False
    if abs(seq - golden.sequence_number) > tolerance_sequences:
        return False
    excerpt = (predicted.get("raw_excerpt") or "").lower()
    if golden.excerpt_contains.lower() not in excerpt:
        return False
    return True


def match_conflict(
    predicted: dict,
    golden: GoldenConflict,
    tolerance_sequences: int = 2,
) -> bool:
    """`predicted` is a plain dict with keys: entity_name, attribute,
    prior_sequence, current_sequence (already resolved by the caller from
    unit_id -> sequence_number).

    Matches if entity_name (case-insensitive), attribute (exact), and both
    prior_sequence/current_sequence are within tolerance_sequences of the
    golden values.
    """
    if predicted.get("entity_name", "").strip().lower() != golden.entity_name.strip().lower():
        return False
    if predicted.get("attribute", "") != golden.attribute:
        return False
    try:
        prior = int(predicted.get("prior_sequence"))
        current = int(predicted.get("current_sequence"))
    except (TypeError, ValueError):
        return False
    if abs(prior - golden.prior_sequence) > tolerance_sequences:
        return False
    if abs(current - golden.current_sequence) > tolerance_sequences:
        return False
    return True


def match_verdict(
    predicted: dict,
    golden: GoldenConflict,
    tolerance_sequences: int = 2,
) -> bool:
    """A verdict matches if the underlying conflict matches (same rule as
    match_conflict) AND predicted["status"] == golden.expected_verdict.
    `predicted` has the same keys as match_conflict plus "status"."""
    if not match_conflict(predicted, golden, tolerance_sequences=tolerance_sequences):
        return False
    return predicted.get("status") == golden.expected_verdict


def compute_metrics(
    phase: str,
    predicted: list[dict],
    golden: list,
    match_fn: Callable[[dict, Any], bool],
) -> PhaseMetrics:
    """Greedy one-to-one matching: each predicted item is matched against
    the first not-yet-matched golden item that match_fn accepts. Unmatched
    predicted items are false positives; unmatched golden items are false
    negatives.

    details entries: {"status": "TP"|"FP"|"FN", "predicted": dict|None, "golden": <golden item>|None}
    """
    tp = 0
    fp = 0
    matched_golden: set[int] = set()
    details: list[dict] = []

    for pred in predicted:
        matched = False
        for i, gold in enumerate(golden):
            if i not in matched_golden and match_fn(pred, gold):
                tp += 1
                matched_golden.add(i)
                matched = True
                details.append({"status": "TP", "predicted": pred, "golden": gold})
                break
        if not matched:
            fp += 1
            details.append({"status": "FP", "predicted": pred, "golden": None})

    fn = 0
    for i, gold in enumerate(golden):
        if i not in matched_golden:
            fn += 1
            details.append({"status": "FN", "predicted": None, "golden": gold})

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return PhaseMetrics(
        phase=phase,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        details=details,
    )
