"""Loading helpers. Systems may use load_task only; load_gold is for evaluation/leakage code."""
from __future__ import annotations
import json, os
from .generate import DATA

TEST_SPLITS = ["test_id", "test_ood_lex", "test_ood_ent", "test_ood_struct", "test_ood_nonlinear",
               "test_ood_length", "test_ood_distract", "test_ood_evorder", "test_challenge"]


def _read(path):
    with open(path) as f:
        return [json.loads(l) for l in f]


def load_task(split: str, data_dir: str = DATA):
    return _read(os.path.join(data_dir, f"{split}.task.jsonl"))


def load_gold(split: str, data_dir: str = DATA):
    return _read(os.path.join(data_dir, f"{split}.gold.jsonl"))
