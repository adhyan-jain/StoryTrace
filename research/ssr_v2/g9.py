"""G9 gate (preregistration section 9 + Amendment 1). Runs BEFORE any LLM. Writes results/v2/g9.json and results/V2_G9_DIAGNOSTIC.md.
Thresholds (fixed in the preregistration): (a) pair-both-correct UCB<=0.02, (b) item semantic state-EM UCB<=0.55, (c') accuracy on
pair-differential claims UCB<=0.55, (d) story-blind Bayes bound<=0.55, (e) story-replay oracle>=0.98 on test_main and set_valued,
(f) oracles agree on every item (enforced at generation: final_state raises on disagreement), (g) zero validator violations."""
from __future__ import annotations
import json, os, sys
from collections import Counter, defaultdict
import numpy as np
from .attackers import Attackers
from .build import DATA
from .replay import predict_final
from .scorers import score_item
from .validators import validate_split

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def load(name):
    T = [json.loads(l) for l in open(os.path.join(DATA, f"{name}.task.jsonl"))]
    G = [json.loads(l) for l in open(os.path.join(DATA, f"{name}.gold.jsonl"))]
    return T, G


def ucb(vals, f, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(vals)
    s = [f([vals[j] for j in rng.integers(0, n, n)]) for _ in range(B)]
    return float(np.percentile(s, 97.5))


def per_pair(T, G, preds):
    """-> list of per-pair dicts with item semantic correctness for A,B and pair-differential claim hits."""
    byp = defaultdict(dict)
    for t, g in zip(T, G):
        if t["member"] in ("A", "B"):
            byp[t["pair_id"]][t["member"]] = (t, g)
    rows = []
    for pid, m in byp.items():
        (ta, ga), (tb, gb) = m["A"], m["B"]
        sa, sb = score_item(ta, ga, preds[ta["item_id"]]), score_item(tb, gb, preds[tb["item_id"]])
        d = ga["meta"]["evidence_slot"]
        cl = {c["id"]: c for c in ta["claims"]}
        diff = [i for i in ga["final"] if ga["final"][i] != gb["final"][i] and cl[i]["slot"] >= d]
        hit = sum(preds[ta["item_id"]].get(i) == ga["final"][i] for i in diff) + sum(preds[tb["item_id"]].get(i) == gb["final"][i] for i in diff)
        rows.append({"a": sa["semantic"], "b": sb["semantic"], "diff_n": 2 * len(diff), "diff_hit": hit, "depth": ga["meta"]["depth"], "stratum": ga["meta"]["stratum"]})
    return rows


def summarize(rows):
    return {"item_sem_em": float(np.mean([(r["a"] + r["b"]) / 2 for r in rows])), "pair_both": float(np.mean([r["a"] and r["b"] for r in rows])),
            "diff_claim_acc": sum(r["diff_hit"] for r in rows) / max(1, sum(r["diff_n"] for r in rows))}


def bayes_bound(T, G):
    groups = defaultdict(list)
    for t, g in zip(T, G):
        if t["member"] in ("A", "B"):
            groups[(t["evidence"], tuple((c["attr"], c["entity"], c["slot"], c["question"]) for c in t["claims"]))].append(g)
    hit = tot = pair_ok = npairs = 0
    for gs in groups.values():
        best = max(gs, key=lambda cand: sum(cand["final"] == o["final"] for o in gs))
        ok = [best["final"] == o["final"] for o in gs]
        hit += sum(ok)
        tot += len(gs)
        pair_ok += all(ok)
        npairs += 1
    return {"item_level": hit / tot, "pair_both": pair_ok / npairs, "groups": npairs}


def main():
    Ttr, Gtr = load("train")
    Tm, Gm = load("test_main")
    Ts, Gs = load("set_valued")
    A = Attackers(Ttr, Gtr)
    out = {"attackers": {}}
    rng = np.random.default_rng(0)
    for name in Attackers.NAMES:
        preds = {t["item_id"]: A.predict(name, t, rng) for t in Tm}
        rows = per_pair(Tm, Gm, preds)
        s = summarize(rows)
        s["ucb_pair_both"] = ucb(rows, lambda R: np.mean([r["a"] and r["b"] for r in R]))
        s["ucb_item_sem_em"] = ucb(rows, lambda R: np.mean([(r["a"] + r["b"]) / 2 for r in R]))
        s["ucb_diff_claim_acc"] = ucb(rows, lambda R: sum(r["diff_hit"] for r in R) / max(1, sum(r["diff_n"] for r in R)))
        s["pass_a"], s["pass_b"], s["pass_c"] = s["ucb_pair_both"] <= 0.02, s["ucb_item_sem_em"] <= 0.55, s["ucb_diff_claim_acc"] <= 0.55
        out["attackers"][name] = s
    out["bayes_bound"] = bayes_bound(Tm, Gm)
    rep = {}
    for nm, (T, G) in (("test_main", (Tm, Gm)), ("set_valued", (Ts, Gs)), ("train", (Ttr, Gtr))):
        rows = [score_item(t, g, predict_final(t)) for t, g in zip(T, G)]
        rep[nm] = {"semantic": float(np.mean([r["semantic"] for r in rows])), "strict": float(np.mean([r["strict"] for r in rows])), "n": len(rows)}
    out["replay_oracle"] = rep
    out["validators"] = {nm: validate_split(*load(nm)) for nm in ("train", "dev", "test_main")}
    for nm in out["validators"]:
        out["validators"][nm]["violations"] = dict(list(out["validators"][nm]["violations"].items())[:10])
    # composition diagnostics
    cat = Counter((g["meta"]["stratum"], g["meta"]["category"]) for g in Gm)
    out["composition"] = {"by_stratum_category": {f"{a}|{b}": n for (a, b), n in sorted(cat.items())},
                          "n_events_by_stratum": {s: sorted(Counter(g["meta"]["n_events"] for g in Gm if g["meta"]["stratum"] == s).items()) for s in sorted({g["meta"]["stratum"] for g in Gm})},
                          "n_sentences_mean_by_stratum": {s: float(np.mean([g["meta"]["n_sentences"] for g in Gm if g["meta"]["stratum"] == s])) for s in sorted({g["meta"]["stratum"] for g in Gm})},
                          "pairs_by_pair_category": dict(Counter(g["meta"]["pair_cat"] for g in Gm if g["member"] == "A"))}
    a_ok = all(v["pass_a"] and v["pass_b"] and v["pass_c"] for v in out["attackers"].values())
    d_ok = out["bayes_bound"]["item_level"] <= 0.55
    e_ok = rep["test_main"]["semantic"] >= 0.98 and rep["set_valued"]["semantic"] >= 0.98
    g_ok = all(v["pairs_with_violations"] == 0 for v in out["validators"].values())
    out["G9"] = {"attackers_abc": a_ok, "bayes_d": d_ok, "replay_e": e_ok, "validators_g": g_ok, "PASS": bool(a_ok and d_ok and e_ok and g_ok)}
    json.dump(out, open(os.path.join(RES, "v2", "g9.json"), "w"), indent=1)
    L = ["# V2 G9 diagnostic (generated by research/ssr_v2/g9.py; no LLM involved)", "", f"**G9: {'PASS' if out['G9']['PASS'] else 'FAIL'}**  {json.dumps(out['G9'])}", "",
         "| attacker | item sem-EM | pair-both | diff-claim acc | UCB item | UCB pair-both | UCB diff-claim | a | b | c' |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, s in out["attackers"].items():
        L.append(f"| {n} | {s['item_sem_em']:.3f} | {s['pair_both']:.3f} | {s['diff_claim_acc']:.3f} | {s['ucb_item_sem_em']:.3f} | {s['ucb_pair_both']:.3f} | {s['ucb_diff_claim_acc']:.3f} | {s['pass_a']} | {s['pass_b']} | {s['pass_c']} |")
    L += ["", f"Story-blind Bayes bound (any story-blind function): item-level {out['bayes_bound']['item_level']:.3f}, pair-both {out['bayes_bound']['pair_both']:.3f} over {out['bayes_bound']['groups']} input groups.",
          f"Story-replay oracle (text only): {json.dumps(rep)}", f"Validators: { {k: (v['pairs'], v['pairs_with_violations']) for k, v in out['validators'].items()} } (pairs, pairs with violations)", "",
          "## Composition", "```", json.dumps(out["composition"], indent=1), "```"]
    open(os.path.join(RES, "V2_G9_DIAGNOSTIC.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
