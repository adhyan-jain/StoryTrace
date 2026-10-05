"""Join raw model outputs / baseline predictions with task + gold; produce per-item count vectors."""
from __future__ import annotations
import json, os
from collections import Counter
from typing import Dict
import numpy as np
from .io import load_gold, load_task
from .metrics import item_counts
from .run import RAW
from .systems import common as C
from .systems import rules, symbolic


def load_raw(model: str, system: str):
    path = os.path.join(RAW, model.replace(":", "_"), f"{system}.jsonl")
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def llm_predictions(model: str, system: str, split: str, tasks: Dict[str, dict]):
    """-> {item_id: {claim_id: (label, value)}}, plus {item_id: qa_answer} for p5, and invalid counts."""
    rows = [r for r in load_raw(model, system) if r["split"] == split]
    by_item: Dict[str, list] = {}
    for r in rows:
        by_item.setdefault(r["item_id"], []).append(r)
    preds, answers = {}, {}
    for iid, rs in by_item.items():
        t = tasks[iid]
        if system == "p5_direct_qa":
            answers[iid] = C.parse_answer(rs[0]["content"])
            continue
        parsed = [C.parse_delta(system, r["content"], t)[0] for r in rs]
        if len(parsed) == 1:
            preds[iid] = parsed[0]
        else:  # self-consistency: per-claim majority vote over (label, value); ties -> KEEP, then first seen
            agg = {}
            for c in t["claims"]:
                votes = Counter(p[c["id"]] for p in parsed)
                top = max(votes.values())
                cands = [v for v, n in votes.items() if n == top]
                agg[c["id"]] = ("KEEP", "") if ("KEEP", "") in cands else cands[0]
            preds[iid] = agg
    return preds, answers


def counts_for(preds: Dict[str, dict], split: str):
    tasks = {t["item_id"]: t for t in load_task(split)}
    gold = {g["item_id"]: g for g in load_gold(split)}
    return {i: item_counts(tasks[i], gold[i], p) for i, p in preds.items()}, gold


def baseline_predictions(name: str, split: str):
    out = {}
    for t in load_task(split):
        if name == "always_keep":
            out[t["item_id"]] = rules.always_keep(t)
        elif name == "symbolic":
            out[t["item_id"]] = symbolic.predict(t)[0]
        elif name == "symbolic_privileged_grammar":
            out[t["item_id"]] = symbolic.predict(t, privileged=True)[0]
        else:
            raise ValueError(name)
    return out
