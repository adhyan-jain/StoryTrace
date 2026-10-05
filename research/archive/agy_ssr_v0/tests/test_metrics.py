import pytest
from src.evaluation.metrics import compute_revision_metrics

def test_metrics_calculation():
    preds = [{("Alice", "location"): "REVISE", ("Bob", "location"): "KEEP"}]
    golds = [{("Alice", "location"): "REVISE", ("Bob", "location"): "KEEP"}]
    m = compute_revision_metrics(preds, golds)
    assert m["revision_precision"] == 1.0
    assert m["revision_recall"] == 1.0
    assert m["preservation_accuracy"] == 1.0
    assert m["delta_exact_match"] == 1.0
