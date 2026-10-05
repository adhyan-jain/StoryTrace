"""Metrics for selective state revision. Value-aware, per-claim, with per-item count vectors so that cluster
bootstrap (resampling STORIES) can recompute every ratio exactly.

Definitions (claim = one ledger fact; gold/pred label in KEEP/REVISE/CONFLICT, REVISE carries a value):
  exact(claim)          : labels equal AND, for REVISE, normalised values equal. INVALID/missing predictions are never exact.
  revision_precision    : #(pred REVISE & gold REVISE & value equal) / #pred REVISE            [undefined if no pred REVISE -> None]
  revision_recall       : same numerator / #gold REVISE
  preservation_accuracy : #(gold KEEP & pred KEEP) / #gold KEEP                                [strict: INVALID is not KEEP]
  collateral_claim_rate : #(gold KEEP & pred in {REVISE, CONFLICT}) / #gold KEEP               [excludes INVALID; differs from 1-preservation by invalid_rate]
  unsupported_item_rate : share of items with >=1 collateral claim                             [item-level, NOT equivalent to the claim-level rate]
  conflict_recall/prec  : on CONFLICT labels (exact claim)
  dependent_recall      : revision_recall restricted to gold REVISE claims on derived attribute `proploc`
  temporal_scope_acc    : exact-rate over claims sharing (attr, entity) with a gold REVISE, on items whose change is temporally bounded
  delta_exact_match     : share of items where every claim is exact
Failure modes: always-KEEP gets preservation 1.0 / recall 0; revise-everything gets recall ~1 / preservation 0 (see tests).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np
from .systems.common import norm

KEYS = ["items", "exact_items", "collateral_items", "tp_rev", "pred_rev", "gold_rev", "keep_total", "keep_ok", "keep_changed",
        "conf_gold", "conf_tp", "conf_pred", "invalid", "claims", "dep_gold", "dep_tp", "temp_n", "temp_ok", "label_tp_rev"]
IDX = {k: i for i, k in enumerate(KEYS)}


def item_counts(task: dict, gold: dict, pred: Dict[str, Tuple[str, str]]) -> np.ndarray:
    v = np.zeros(len(KEYS))
    v[IDX["items"]] = 1
    all_exact, collateral = True, False
    grp = {(c["attr"], c["entity"]) for c in task["claims"] if gold["labels"][c["id"]]["label"] == "REVISE"}
    bounded = gold["meta"]["scope_bounded"]
    for c in task["claims"]:
        g = gold["labels"][c["id"]]
        gl, gv = g["label"], norm(g["value"])
        pl, pv = pred.get(c["id"], ("INVALID", ""))
        exact = (gl == pl) and (gl != "REVISE" or gv == pv)
        all_exact &= exact
        v[IDX["claims"]] += 1
        v[IDX["invalid"]] += pl == "INVALID"
        if pl == "REVISE":
            v[IDX["pred_rev"]] += 1
            v[IDX["tp_rev"]] += exact and gl == "REVISE"
        if gl == "REVISE":
            v[IDX["gold_rev"]] += 1
            v[IDX["label_tp_rev"]] += pl == "REVISE"
            if c["attr"] == "proploc":
                v[IDX["dep_gold"]] += 1
                v[IDX["dep_tp"]] += exact
        if gl == "KEEP":
            v[IDX["keep_total"]] += 1
            v[IDX["keep_ok"]] += pl == "KEEP"
            if pl in ("REVISE", "CONFLICT"):
                v[IDX["keep_changed"]] += 1
                collateral = True
        if gl == "CONFLICT":
            v[IDX["conf_gold"]] += 1
            v[IDX["conf_tp"]] += exact
        if pl == "CONFLICT":
            v[IDX["conf_pred"]] += 1
        if bounded and (c["attr"], c["entity"]) in grp:
            v[IDX["temp_n"]] += 1
            v[IDX["temp_ok"]] += exact
    v[IDX["exact_items"]] = all_exact
    v[IDX["collateral_items"]] = collateral
    return v


def _r(a: float, b: float) -> Optional[float]:
    return None if b == 0 else a / b


def summarize(c: np.ndarray) -> Dict[str, Optional[float]]:
    g = lambda k: c[IDX[k]]
    p, r = _r(g("tp_rev"), g("pred_rev")), _r(g("tp_rev"), g("gold_rev"))
    return {
        "revision_precision": p, "revision_recall": r,
        "revision_f1": None if p is None or r is None or (p + r) == 0 else 2 * p * r / (p + r),
        "preservation_accuracy": _r(g("keep_ok"), g("keep_total")),
        "collateral_claim_rate": _r(g("keep_changed"), g("keep_total")),
        "unsupported_item_rate": _r(g("collateral_items"), g("items")),
        "conflict_recall": _r(g("conf_tp"), g("conf_gold")), "conflict_precision": _r(g("conf_tp"), g("conf_pred")),
        "dependent_recall": _r(g("dep_tp"), g("dep_gold")), "temporal_scope_acc": _r(g("temp_ok"), g("temp_n")),
        "delta_exact_match": _r(g("exact_items"), g("items")), "invalid_rate": _r(g("invalid"), g("claims")),
        "n_items": g("items"),
    }


def per_story(counts: Dict[str, np.ndarray], gold_by_item: Dict[str, dict]):
    """-> (story_ids, matrix[S, K]) summing item vectors within each story."""
    sids = sorted({gold_by_item[i]["story_id"] for i in counts})
    ix = {s: j for j, s in enumerate(sids)}
    M = np.zeros((len(sids), len(KEYS)))
    for i, v in counts.items():
        M[ix[gold_by_item[i]["story_id"]]] += v
    return sids, M
