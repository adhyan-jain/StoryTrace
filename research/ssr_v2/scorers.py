"""V2 scorers (strict + semantic, set-valued gold, invariants, per-claim error classes). Pure functions of (task, gold, prediction).
Prediction format: {claim_id: final value string}; missing / out-of-domain -> invalid."""
from __future__ import annotations
import re
from typing import Dict, List, Optional

SYN = {"no one": "nobody", "none": "nobody", "nothing": "nobody", "noone": "nobody", "unattended": "nobody",
       "hurt": "injured", "wounded": "injured", "healthy": "unharmed", "fine": "unharmed", "uninjured": "unharmed", "well": "unharmed"}


def norm(v) -> str:
    if not isinstance(v, str):
        return ""
    v = v.strip().strip('."\'').lower()
    v = re.sub(r"^(in|to|at|by)\s+", "", v)
    v = re.sub(r"^the\s+", "", v)
    return SYN.get(v.strip(), v.strip())


def canon(v: str) -> str:
    return norm(v)


def in_domain(task_claim: dict, v) -> bool:
    return isinstance(v, str) and norm(v) in {norm(x) for x in task_claim["domain"]}


def inconsistent(task: dict, pred: Dict[str, str]) -> bool:
    """Cross-claim invariant: if holder(p,s)=X, loc(X,s)=M and proploc(p,s)=L are all answered at the same slot, L must equal M;
    and holder(p,s)=nobody with a stated holder elsewhere at the same slot is impossible by construction (single value per claim)."""
    by = {(c["attr"], c["entity"], c["slot"]): norm(pred.get(c["id"], "")) for c in task["claims"]}
    for (attr, ent, s), v in by.items():
        if attr == "holder" and v and v != "nobody":
            L = by.get(("proploc", ent, s))
            M = by.get(("loc", v, s))
            if L and M and L != M:
                return True
    return False


def score_item(task: dict, gold: dict, pred: Dict[str, str]) -> dict:
    claims = {c["id"]: c for c in task["claims"]}
    P = {i: pred.get(i) for i in claims}
    invalid = {i for i, c in claims.items() if not in_domain(c, P[i])}
    prior = {i: canon(v) for i, v in gold["prior"].items()}
    worlds = [{i: canon(v) for i, v in w.items()} for w in gold["valid_final"]]
    # strict: exact canonical string equality with the single canonical state (first valid world)
    strict = all(P[i] == gold["final"][i] for i in claims)
    pn = {i: norm(P[i]) if i not in invalid else None for i in claims}
    sem = any(all(pn[i] == w[i] for i in claims) for w in worlds)
    # per-claim classes against the best-matching valid world
    best = max(worlds, key=lambda w: sum(pn[i] == w[i] for i in claims))
    ev_ents = {gold["world"]["evidence"].get(k) for k in ("actor", "prop", "target")} - {None, ""}
    cls, c = {}, {"req": 0, "req_ok": 0, "keep": 0, "keep_ok": 0, "collateral": 0, "over": 0, "under": 0, "wrongval": 0, "invalid": len(invalid), "unrelated_edit": 0}
    for i, cl in claims.items():
        changed = best[i] != prior[i]
        if i in invalid:
            cls[i] = "invalid"
            c["req"] += changed
            c["keep"] += not changed
            continue
        if changed:
            c["req"] += 1
            if pn[i] == best[i]:
                cls[i] = "correct_revision"
                c["req_ok"] += 1
            elif pn[i] == prior[i]:
                cls[i] = "under_revision"
                c["under"] += 1
            else:
                cls[i] = "wrong_value_revision"
                c["wrongval"] += 1
        else:
            c["keep"] += 1
            if pn[i] == prior[i]:
                cls[i] = "correct_preserve"
                c["keep_ok"] += 1
            else:
                cls[i] = "over_revision"
                c["over"] += 1
                c["collateral"] += 1
                if cl["entity"] not in ev_ents:
                    cls[i] = "collateral_unrelated"
                    c["unrelated_edit"] += 1
    return {"strict": bool(strict), "semantic": bool(sem), "inconsistent": inconsistent(task, {i: pn[i] or "" for i in claims}),
            "classes": cls, **c, "n_claims": len(claims)}


def aggregate(rows: List[dict]) -> dict:
    n = len(rows)
    req, keep = sum(r["req"] for r in rows), sum(r["keep"] for r in rows)
    return {"n_items": n, "state_em_strict": sum(r["strict"] for r in rows) / n, "state_em_semantic": sum(r["semantic"] for r in rows) / n,
            "required_change_recall": (sum(r["req_ok"] for r in rows) / req) if req else None,
            "preservation": (sum(r["keep_ok"] for r in rows) / keep) if keep else None,
            "collateral_edit_rate": (sum(r["collateral"] for r in rows) / keep) if keep else None,
            "under_revision_rate": (sum(r["under"] for r in rows) / req) if req else None,
            "wrong_value_rate": (sum(r["wrongval"] for r in rows) / req) if req else None,
            "invalid_rate": sum(r["invalid"] for r in rows) / sum(r["n_claims"] for r in rows),
            "inconsistent_rate": sum(r["inconsistent"] for r in rows) / n,
            "unrelated_edit_rate": (sum(r["unrelated_edit"] for r in rows) / keep) if keep else None}
