"""Shared helpers for the adversarial audit (analysis only; the benchmark definition is never modified).

- rebuild(): re-create a task/gold record pair from a stored world, recomputing gold with BOTH oracles.
- evaluation helpers that reuse metrics.item_counts / per_story / stats.boot_ci unchanged, plus label-level metrics.
"""
from __future__ import annotations
import json, os, random
from typing import Dict, List, Optional, Tuple
import numpy as np
from .. import oracle_a, oracle_b
from ..generate import category
from ..io import load_gold, load_task
from ..leakage import story_from_world
from ..metrics import item_counts, per_story, summarize
from .. import realize as R0
from .. import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "results")
ADV = os.path.join(RESULTS, "adv")
ADV_DATA = os.path.join(ADV, "data")
LABELS = ["KEEP", "REVISE", "CONFLICT"]


def write_jsonl(path: str, rows) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def keys_of(task: dict) -> List[Tuple[str, str, int]]:
    return [(c["attr"], c["entity"], c["slot"]) for c in task["claims"]]


def rebuild(task: dict, gold: dict, *, story=None, ev=None, keys=None, probe_key=None, held: Optional[bool] = None,
            shuffle: Optional[bool] = None, realize=R0, seed="x", permute_claims: bool = False,
            item_id: Optional[str] = None, meta_update: Optional[dict] = None):
    """Re-realise one item. Story/evidence/claim keys default to the stored ones; gold is recomputed by both oracles."""
    st0, ev0 = story_from_world(gold["world"])
    story = story or st0
    ev = ev or ev0
    old_keys = keys_of(task)
    keys = list(keys or old_keys)
    if probe_key is None:
        probe_key = next((k for c, k in zip(task["claims"], old_keys) if c["id"] == task["probe"]["claim_id"]), keys[0])
    if probe_key not in keys:
        probe_key = keys[0]
    rng = random.Random(f"adv/{seed}/{task['item_id']}")
    if permute_claims:
        rng.shuffle(keys)
    held = gold["meta"]["template_heldout"] if held is None else held
    narr_shuffle = (gold["meta"]["narration"] == "shuffled") if shuffle is None else shuffle
    prior_a, prior_b = oracle_a.values(story, keys), oracle_b.values(story, keys)
    assert prior_a == prior_b, "oracle disagreement on prior values"
    ga, gb = oracle_a.gold(story, ev, keys), oracle_b.gold(story, ev, keys)
    assert all(ga[k] == gb[k] for k in keys), "oracle disagreement on gold"
    ids = {k: f"c{i + 1}" for i, k in enumerate(keys)}
    iid = item_id or task["item_id"]
    new_task = {
        "item_id": iid,
        "story": realize.story_sentences(story, random.Random(rng.random()), held, narr_shuffle),
        "evidence": realize.evidence_text(ev, story, random.Random(rng.random()), held),
        "claims": [{"id": ids[k], "entity": k[1], "attr": k[0], "slot": k[2], "value": prior_a[k],
                    "statement": R0.claim_statement(k, prior_a[k])} for k in keys],
        "probe": {"claim_id": ids[probe_key], "question": R0.question_text(probe_key)},
    }
    chg = [k for k in keys if ga[k][0] == "REVISE"]
    last = max(e.slot for e in story.events)
    meta = dict(gold["meta"])
    meta.update({
        "category": category(ga), "evidence_slot": ev.slot, "slot_rel": "past" if ev.slot < last else "future",
        "n_changed": len(chg), "n_claims": len(keys), "template_heldout": held,
        "narration": "shuffled" if narr_shuffle else "linear",
        "n_story_sentences": len(new_task["story"]),
        "scope_bounded": any(v[0] == "KEEP" and k[2] > ev.slot and (k[0], k[1]) in {(c[0], c[1]) for c, w in ga.items() if w[0] == "REVISE"}
                             for k, v in ga.items()),
        "has_dependent_change": any(k[0] == "proploc" for k in chg),
        "oracle_agree": True,
    })
    meta.update(meta_update or {})
    new_gold = {
        "item_id": iid, "story_id": gold["story_id"], "split": gold["split"],
        "labels": {ids[k]: {"label": ga[k][0], "value": ga[k][1]} for k in keys},
        "probe_answer": ga[probe_key][1] if ga[probe_key][0] == "REVISE" else prior_a[probe_key],
        "meta": meta, "world": gold["world"], "base_item_id": gold["item_id"],
    }
    return new_task, new_gold


# ----------------------------------------------------------------------------- evaluation
def label_vectors(task: dict, gold: dict, pred: Dict[str, Tuple[str, str]]):
    y = [gold["labels"][c["id"]]["label"] for c in task["claims"]]
    p = [pred.get(c["id"], ("INVALID", ""))[0] for c in task["claims"]]
    return y, p


def macro_f1(y: List[str], p: List[str]) -> float:
    f = []
    for lab in LABELS:
        tp = sum(a == lab and b == lab for a, b in zip(y, p))
        fp = sum(a != lab and b == lab for a, b in zip(y, p))
        fn = sum(a == lab and b != lab for a, b in zip(y, p))
        if tp + fp + fn == 0:
            continue
        f.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f)) if f else float("nan")


def evaluate(preds: Dict[str, dict], tasks: List[dict], golds: List[dict]) -> dict:
    """-> value-aware counts per item, label-level exactness per item, per-claim label errors (all keyed by item_id)."""
    T = {t["item_id"]: t for t in tasks}
    G = {g["item_id"]: g for g in golds}
    counts, label_ok, claim_err = {}, {}, {}
    ys, ps = [], []
    for iid, p in preds.items():
        counts[iid] = item_counts(T[iid], G[iid], p)
        y, pl = label_vectors(T[iid], G[iid], p)
        label_ok[iid] = all(a == b for a, b in zip(y, pl))
        claim_err[iid] = [a != b for a, b in zip(y, pl)]
        ys += y
        ps += pl
    return {"counts": counts, "label_ok": label_ok, "claim_err": claim_err, "claim_macro_f1": macro_f1(ys, ps), "gold_by_item": G}


def summary_with_ci(ev: dict, metrics=("delta_exact_match", "preservation_accuracy", "revision_recall"), b: int = 1000) -> dict:
    sids, M = per_story(ev["counts"], ev["gold_by_item"])
    out = {"n_items": len(ev["counts"]), "n_stories": len(sids), "claim_macro_f1": ev["claim_macro_f1"]}
    for m in metrics:
        est, lo, hi = stats.boot_ci(M, m, b=b)
        out[m] = [est, lo, hi]
    s = summarize(M.sum(0))
    out["collateral_claim_rate"] = s["collateral_claim_rate"]
    out["revision_precision"] = s["revision_precision"]
    out["conflict_recall"] = s["conflict_recall"]
    out["label_em"] = float(np.mean(list(ev["label_ok"].values()))) if ev["label_ok"] else float("nan")
    return out


def load_split(split: str, data_dir: Optional[str] = None):
    if data_dir:
        return load_task(split, data_dir), load_gold(split, data_dir)
    return load_task(split), load_gold(split)
