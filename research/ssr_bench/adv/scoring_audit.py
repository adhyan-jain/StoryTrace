"""Scoring audit (analysis only; metrics.py stays the headline metric). Re-scores the SAME raw LLM outputs with lenient scorers.

  S0  current exact delta-EM (value-aware, strict)           S1  label-only (REVISE value ignored)
  S2  state-equivalence: 'REVISE: <prior value>' counts as KEEP (identical resulting state)
  S2b state-only: only resulting per-claim values matter (CONFLICT == KEEP, flags ignored)
  S3  lenient CONFLICT: CONFLICT accepted on any ledger claim in the same constant-value interval as the gold CONFLICT claim
      (all of them are contradicted by the evidence under the persistence rule), computed by oracle replay
  S5  INVALID-tolerant: INVALID counted as KEEP
  SALL = S2 + S3 + S5 applied together (value errors and wrong flags remain errors)
Artifact share = share of S0-failing items that pass SALL. It is an UPPER bound on metric-artifact errors (a pass under SALL means
the output is state-equivalent to gold under the rules); it never rescues wrong values, missed revisions or collateral revisions.
Writes results/adv/scoring_audit.json and adjudication_sample.json.
"""
from __future__ import annotations
import json, os, random
from collections import Counter, defaultdict
import numpy as np
from .. import oracle_a
from ..evaluate import llm_predictions
from ..io import TEST_SPLITS, load_gold, load_task
from ..leakage import story_from_world
from ..systems import common as C
from .common import ADV, keys_of

MODELS = ["qwen2.5:7b", "llama3:latest", "qwen3:8b", "mistral:7b"]
SYSTEMS = ["p1_zero_shot_delta", "p2_explicit_revision", "p3_regenerate", "p4_self_consistency"]


def conflict_set(gold: dict, task: dict):
    """Ledger claim ids contradicted by the evidence under persistence (same attr/entity, same constant-value interval)."""
    ck = [(c["id"], (c["attr"], c["entity"], c["slot"])) for c in task["claims"] if gold["labels"][c["id"]]["label"] == "CONFLICT"]
    if not ck:
        return set()
    story, _ = story_from_world(gold["world"])
    snaps, _ = oracle_a.replay(story, story.events)
    cid0, (attr, ent, cs) = ck[0]
    v = oracle_a._read(snaps[cs], attr, ent)
    ok = set()
    for c in task["claims"]:
        if c["attr"] == attr and c["entity"] == ent:
            lo, hi = sorted((c["slot"], cs))
            if all(oracle_a._read(snaps[s], attr, ent) == v for s in range(lo, hi + 1)):
                ok.add(c["id"])
    return ok


def score_item(task, gold, pred, cset):
    claims = task["claims"]
    prior = {c["id"]: C.norm(c["value"]) for c in claims}
    G = {c["id"]: (gold["labels"][c["id"]]["label"], C.norm(gold["labels"][c["id"]]["value"])) for c in claims}
    P = {c["id"]: pred.get(c["id"], ("INVALID", "")) for c in claims}
    exact = lambda g, p: g[0] == p[0] and (g[0] != "REVISE" or g[1] == p[1])
    s0 = all(exact(G[i], P[i]) for i in G)
    s1 = all(G[i][0] == P[i][0] for i in G)

    def lenient(P, rev_same, inval, conf):
        Q = {}
        for i, p in P.items():
            if inval and p[0] == "INVALID":
                p = ("KEEP", "")
            if rev_same and p[0] == "REVISE" and p[1] == prior[i]:
                p = ("KEEP", "")
            Q[i] = p
        Gx = dict(G)
        if conf and cset and any(Q[i][0] == "CONFLICT" for i in cset) and all(Q[i][0] in ("CONFLICT", "KEEP") for i in cset):
            for i in cset:
                if Q[i][0] == "CONFLICT":
                    Gx[i] = ("CONFLICT", "")
            # gold CONFLICT claim satisfied by any in-set CONFLICT
            for i in cset:
                if G[i][0] == "CONFLICT":
                    Gx[i] = Q[i] if Q[i][0] == "CONFLICT" else ("CONFLICT", "") if any(Q[j][0] == "CONFLICT" for j in cset) else G[i]
                    Q[i] = ("CONFLICT", "")
        return all(exact(Gx[i], Q[i]) for i in G)

    s2 = lenient(P, True, False, False)
    s3 = lenient(P, False, False, True)
    s5 = lenient(P, False, True, False)
    sall = lenient(P, True, True, True)
    gs = {i: (G[i][1] if G[i][0] == "REVISE" else prior[i]) for i in G}
    ps = {i: (P[i][1] if P[i][0] == "REVISE" else prior[i]) if P[i][0] != "INVALID" else None for i in G}
    s2b = all(gs[i] == ps[i] for i in G)
    return dict(S0=s0, S1=s1, S2=s2, S2b=s2b, S3=s3, S5=s5, SALL=sall)


def main(b=2000):
    rng = np.random.default_rng(0)
    out, rows_all, sample_pool = {}, [], []
    for sp in TEST_SPLITS:
        tasks = {t["item_id"]: t for t in load_task(sp)}
        gold = {g["item_id"]: g for g in load_gold(sp)}
        csets = {i: conflict_set(g, tasks[i]) for i, g in gold.items()}
        for m in MODELS:
            for s in SYSTEMS:
                preds, _ = llm_predictions(m, s, sp, tasks)
                for iid, p in preds.items():
                    sc = score_item(tasks[iid], gold[iid], p, csets[iid])
                    rows_all.append(dict(model=m, system=s, split=sp, story=gold[iid]["story_id"], item=iid,
                                         cat=gold[iid]["meta"]["category"], **sc))
                    if s == "p2_explicit_revision" and sp == "test_id" and not sc["S0"]:
                        sample_pool.append((m, iid, sc["SALL"]))
    # ------------------------------------------------------------------ summaries (cluster bootstrap over stories)
    def summarize(rows):
        stories = sorted({r["story"] for r in rows})
        ix = {s: [r for r in rows if r["story"] == s] for s in stories}
        def stat(sel):
            R = [r for s in sel for r in ix[s]]
            n = len(R); fail = [r for r in R if not r["S0"]]
            d = {k: float(np.mean([r[k] for r in R])) for k in ("S0", "S1", "S2", "S2b", "S3", "S5", "SALL")}
            d["rescued_share_of_failures"] = (sum(r["SALL"] for r in fail) / len(fail)) if fail else float("nan")
            d["n_items"] = n
            return d
        est = stat(stories)
        bs = [stat([stories[j] for j in rng.integers(0, len(stories), len(stories))]) for _ in range(b // 4)]
        for k in ("S0", "SALL", "rescued_share_of_failures"):
            v = np.array([x[k] for x in bs], float)
            est[k + "_ci"] = [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
        return est
    for m in MODELS:
        for s in SYSTEMS:
            for scope in ("test_id", "all"):
                rows = [r for r in rows_all if r["model"] == m and r["system"] == s and (scope == "all" or r["split"] == "test_id")]
                if rows:
                    out[f"{m}|{s}|{scope}"] = summarize(rows)
    # by category for p2/test_id: where do artifacts live?
    for m in MODELS:
        for cat in ("resolving", "irrelevant", "contradictory"):
            rows = [r for r in rows_all if r["model"] == m and r["system"] == "p2_explicit_revision" and r["split"] == "test_id" and r["cat"] == cat]
            out[f"{m}|p2_explicit_revision|test_id|{cat}"] = {k: float(np.mean([r[k] for r in rows])) for k in ("S0", "S1", "S2", "S2b", "S3", "S5", "SALL")} | {"n_items": len(rows)}
    # equivalence-class facts straight from gold
    eq = {}
    for sp in TEST_SPLITS:
        tasks = {t["item_id"]: t for t in load_task(sp)}
        gold = load_gold(sp)
        sizes = [len(conflict_set(g, tasks[g["item_id"]])) for g in gold if g["meta"]["category"] == "contradictory"]
        keeps = [sum(v["label"] == "KEEP" for v in g["labels"].values()) for g in gold]
        eq[sp] = {"contradictory_items": len(sizes), "mean_conflict_set_size": float(np.mean(sizes)),
                  "share_items_with_multi_claim_conflict_set": float(np.mean([x > 1 for x in sizes])),
                  "mean_KEEP_claims_with_equivalent_REVISE_same_value_form": float(np.mean(keeps))}
    out["equivalence_class"] = eq
    json.dump(out, open(os.path.join(ADV, "scoring_audit.json"), "w"), indent=1)
    # stratified sample for MANUAL adjudication (p2, test_id): 5 failures per model x category = 60 items
    random.seed(0)
    tasks = {t["item_id"]: t for t in load_task("test_id")}
    gold = {g["item_id"]: g for g in load_gold("test_id")}
    sample = []
    cache = {m: llm_predictions(m, "p2_explicit_revision", "test_id", tasks)[0] for m in MODELS}
    for m in MODELS:
        for cat in ("resolving", "irrelevant", "contradictory"):
            pool = [x for x in sample_pool if x[0] == m and gold[x[1]]["meta"]["category"] == cat]
            for _, iid, _ in random.sample(pool, min(5, len(pool))):
                t, g, p = tasks[iid], gold[iid], cache[m][iid]
                diff = [dict(claim=c["statement"], gold=g["labels"][c["id"]], pred=p[c["id"]]) for c in t["claims"]
                        if not (g["labels"][c["id"]]["label"] == p[c["id"]][0] and (g["labels"][c["id"]]["label"] != "REVISE" or C.norm(g["labels"][c["id"]]["value"]) == p[c["id"]][1]))]
                sample.append(dict(model=m, item=iid, category=cat, evidence=t["evidence"], story=t["story"], wrong_claims=diff,
                                   n_wrong=len(diff), n_changed_gold=g["meta"]["n_changed"]))
    json.dump(sample, open(os.path.join(ADV, "adjudication_sample.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k.endswith("p2_explicit_revision|test_id")}, indent=1))
    print("equivalence:", json.dumps(eq["test_id"]))
    print("sample items:", len(sample))


if __name__ == "__main__":
    main()
