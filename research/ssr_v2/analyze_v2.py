"""Analysis of V2 LLM runs (CPU only). Reads results/v2/raw/<cond>/<split>__<model>.jsonl, scores with scorers.py (strict + semantic), writes
results/v2/scored/*.jsonl (per-item scorer outputs, semantic judgments), results/v2/analysis.json and the markdown reports.
Unit of analysis = matched pair (cluster bootstrap over pairs, 10,000 resamples). Contrasts: exact McNemar on items, paired risk difference, Cohen's h, Holm per model."""
from __future__ import annotations
import json, os, sys
from collections import defaultdict
import numpy as np
from scipy.stats import binomtest
from .build import DATA
from .scorers import aggregate, score_item

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
V2 = os.path.join(RES, "v2")
MODELS = ["qwen2.5:7b", "llama3:latest", "qwen3:8b", "mistral:7b"]
B = int(os.environ.get("V2_BOOT", 10000))
rng = np.random.default_rng(0)


def load_split(name):
    name = name.replace("_sub100", "")
    if name.startswith("tf:"):
        d, base = os.path.join(DATA, "transforms", name[3:]), "test_main_sub50"
    else:
        d, base = DATA, name
    T = {json.loads(l)["item_id"]: json.loads(l) for l in open(os.path.join(d, f"{base}.task.jsonl"))}
    G = {json.loads(l)["item_id"]: json.loads(l) for l in open(os.path.join(d, f"{base}.gold.jsonl"))}
    return T, G


def parse(cond, content, t, g):
    try:
        o = json.loads(content)
        assert isinstance(o, dict)
    except Exception:
        return {}
    if cond != "K1-delta":
        return {k: v for k, v in o.items() if isinstance(v, str)}
    out = {}
    for c in t["claims"]:
        s = str(o.get(c["id"], "")).strip()
        u = s.upper()
        if u.startswith("KEEP") or u.startswith("CONFLICT"):
            out[c["id"]] = g["prior"][c["id"]]
        elif u.startswith("REVISE"):
            out[c["id"]] = s.split(":", 1)[1].strip() if ":" in s else ""
    return out


def load_runs(root, cond, split, model):
    path = os.path.join(root, cond, f"{split.replace(':', '_')}__{model.replace(':', '_')}.jsonl")
    if not os.path.exists(path):
        return None
    T, G = load_split(split)
    rows = {}
    for l in open(path):
        r = json.loads(l)
        t, g = T[r["item_id"]], G[r["item_id"]]
        pred = parse(cond, r["content"], t, g)
        s = score_item(t, g, pred)
        rows[r["item_id"]] = dict(s, item=r["item_id"], pair=t["pair_id"], member=t["member"], stratum=g["meta"]["stratum"], depth=g["meta"]["depth"],
                                  category=g["meta"]["category"], pred=pred, error=r["error"], wall_s=r["wall_s"])
    return rows


def pair_boot(rows, f, b=B):
    pairs = defaultdict(list)
    for r in rows:
        pairs[r["pair"]].append(r)
    ids = list(pairs)
    est = f([r for p in ids for r in pairs[p]])
    idx = rng.integers(0, len(ids), size=(b, len(ids)))
    vals = [f([r for j in row for r in pairs[ids[j]]]) for row in idx]
    return est, float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


def mcnemar(a, b):
    """a,b: dict item->bool on shared items. Returns (b01, b10, exact p)."""
    keys = [k for k in a if k in b]
    n01 = sum((not a[k]) and b[k] for k in keys)
    n10 = sum(a[k] and (not b[k]) for k in keys)
    p = binomtest(min(n01, n10), n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return n01, n10, float(p), len(keys)


def holm(ps):
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def cohens_h(p1, p2):
    return float(2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2)))


def f_sem(R):
    return float(np.mean([r["semantic"] for r in R])) if R else np.nan


def f_strict(R):
    return float(np.mean([r["strict"] for r in R])) if R else np.nan


def main(root=os.path.join(V2, "raw"), split_of=None, out_tag=""):
    split_of = split_of or {"K1": "test_main", "K2": "test_main", "K4": "test_main", "PG": "test_main", "S0": "test_main", "K1-fs": "test_main",
                            "K3a": "test_main", "K3b": "test_main", "K1-delta": "test_main_sub100"}
    conds = list(split_of)
    R = {}
    A = {"cells": {}, "contrasts": {}, "pair_consistency": {}, "depth": {}, "decomposition": {}, "classes": {}, "setvalued": {}}
    os.makedirs(os.path.join(V2, "scored"), exist_ok=True)
    for m in MODELS:
        for c in conds:
            rows = load_runs(root, c, split_of[c], m)
            if rows:
                R[(m, c)] = rows
                with open(os.path.join(V2, "scored", f"{c}__{m.replace(':', '_')}{out_tag}.jsonl"), "w") as f:
                    for r in rows.values():
                        f.write(json.dumps({k: v for k, v in r.items()}) + "\n")
                lst = list(rows.values())
                agg = aggregate(lst)
                A["cells"][f"{m}|{c}"] = dict(agg, sem_ci=pair_boot(lst, f_sem, 2000), strict_ci=pair_boot(lst, f_strict, 2000))
                A["classes"][f"{m}|{c}"] = {k: int(sum(1 for r in lst for v in r["classes"].values() if v == k)) for k in
                                           ("correct_revision", "under_revision", "wrong_value_revision", "correct_preserve", "over_revision", "collateral_unrelated", "invalid")}
    # paired contrasts vs K1 (same items), Holm per model
    for m in MODELS:
        fam, raw = {}, {}
        for c in conds:
            if c in ("K1", "S0") or (m, c) not in R or (m, "K1") not in R:
                continue
            a = {k: v["semantic"] for k, v in R[(m, "K1")].items()}
            b = {k: v["semantic"] for k, v in R[(m, c)].items()}
            shared = [k for k in a if k in b]
            n01, n10, p, n = mcnemar(a, b)
            rd = np.mean([b[k] - a[k] for k in shared]) if shared else np.nan
            rows_sh = [dict(pair=R[(m, "K1")][k]["pair"], d=float(b[k]) - float(a[k])) for k in shared]
            est, lo, hi = pair_boot(rows_sh, lambda X: float(np.mean([x["d"] for x in X])), 2000) if shared else (np.nan,) * 3
            fam[c] = p
            raw[c] = dict(vs="K1", n_items=n, k1_only_correct=n10, other_only_correct=n01, risk_diff=float(rd), rd_ci=[lo, hi], p_mcnemar=p,
                          h=cohens_h(np.mean([b[k] for k in shared]), np.mean([a[k] for k in shared])) if shared else None)
        hp = holm(fam) if fam else {}
        for c in raw:
            raw[c]["p_holm"] = hp[c]
            A["contrasts"][f"{m}|{c}"] = raw[c]
    # pair consistency + story tracking (K1 / PG / K2 / K4)
    for (m, c), rows in R.items():
        byp = defaultdict(dict)
        for r in rows.values():
            if r["member"] in ("A", "B"):
                byp[r["pair"]][r["member"]] = r
        if not byp:
            continue
        T, G = load_split(split_of[c].replace("_sub100", ""))
        cnt = {"both": 0, "neither": 0, "A_only": 0, "B_only": 0, "same_output_on_differential_claims": 0, "tracks_difference": 0}
        for pid, mm in byp.items():
            if "A" not in mm or "B" not in mm:
                continue
            ra, rb = mm["A"], mm["B"]
            cnt["both" if ra["semantic"] and rb["semantic"] else "neither" if not (ra["semantic"] or rb["semantic"]) else "A_only" if ra["semantic"] else "B_only"] += 1
            ga, gb = G[ra["item"]], G[rb["item"]]
            d = ga["meta"]["evidence_slot"]
            cl = {x["id"]: x for x in T[ra["item"]]["claims"]}
            diff = [i for i in ga["final"] if ga["final"][i] != gb["final"][i] and cl[i]["slot"] >= d]
            if diff:
                cnt["same_output_on_differential_claims"] += all(ra["pred"].get(i) == rb["pred"].get(i) for i in diff)
                cnt["tracks_difference"] += all(ra["pred"].get(i) == ga["final"][i] and rb["pred"].get(i) == gb["final"][i] for i in diff)
        n = max(1, sum(cnt[k] for k in ("both", "neither", "A_only", "B_only")))
        A["pair_consistency"][f"{m}|{c}"] = dict(cnt, n_pairs=n)
    A["diff_claims"] = {}
    for (m, c), rows in R.items():
        T, G = load_split(split_of[c])
        byp = defaultdict(dict)
        for r in rows.values():
            if r["member"] in ("A", "B"):
                byp[r["pair"]][r["member"]] = r
        hit = tot = 0
        pr = []
        for pid, mm in byp.items():
            if "A" not in mm or "B" not in mm:
                continue
            ra, rb = mm["A"], mm["B"]
            ga, gb = G[ra["item"]], G[rb["item"]]
            cl = {x["id"]: x for x in T[ra["item"]]["claims"]}
            ext = ga["world"].get("chars") is None
            diff = [i for i in ga["final"] if ga["final"][i] != gb["final"][i] and (ext or cl[i]["slot"] >= ga["meta"]["evidence_slot"])]
            h = sum((ra["pred"].get(i) or "").lower() == ga["final"][i].lower() for i in diff) + sum((rb["pred"].get(i) or "").lower() == gb["final"][i].lower() for i in diff)
            hit, tot = hit + h, tot + 2 * len(diff)
            pr.append({"pair": pid, "h": h, "n": 2 * len(diff)})
        if tot:
            A["diff_claims"][f"{m}|{c}"] = {"acc": hit / tot, "n_claims": tot, "ci": pair_boot(pr, lambda X: sum(x["h"] for x in X) / max(1, sum(x["n"] for x in X)), 2000)}
    # depth strata (semantic state-EM) and trend
    for (m, c), rows in R.items():
        lst = list(rows.values())
        strat = {}
        for s in sorted({r["stratum"] for r in lst}):
            sub = [r for r in lst if r["stratum"] == s]
            strat[s] = dict(zip(("est", "lo", "hi"), pair_boot(sub, f_sem, 2000)), n_items=len(sub))
        d14 = None
        a1, a4 = [r for r in lst if r["stratum"] == "D1"], [r for r in lst if r["stratum"] == "D4"]
        if a1 and a4:
            both = a1 + a4
            d14 = pair_boot(both, lambda X: f_sem([r for r in X if r["stratum"] == "D1"]) - f_sem([r for r in X if r["stratum"] == "D4"]), 2000)
        lg = [r for r in lst if r["stratum"] == "D2_long"]
        sh = [r for r in lst if r["stratum"] == "D2"]
        dl = pair_boot(sh + lg, lambda X: f_sem([r for r in X if r["stratum"] == "D2"]) - f_sem([r for r in X if r["stratum"] == "D2_long"]), 2000) if lg and sh else None
        A["depth"][f"{m}|{c}"] = {"by_stratum": strat, "D1_minus_D4": d14, "D2short_minus_D2long": dl}
    # decomposition: prior tracking (S0) vs revision, claim level, K1 and PG
    for m in MODELS:
        if (m, "S0") in R and (m, "K1") in R:
            T, G = load_split(split_of["K1"].replace("_sub100", ""))
            joint = {"ch_s0ok_k1ok": 0, "ch_s0ok": 0, "ch_s0bad_k1ok": 0, "ch_s0bad": 0, "s0_claim_acc": [0, 0]}
            for iid, r0 in R[(m, "S0")].items():
                r1 = R[(m, "K1")].get(iid)
                if not r1:
                    continue
                g = G[iid]
                for cid, pv in g["prior"].items():
                    s0ok = r0["pred"].get(cid) is not None and r0["pred"][cid].lower() == pv.lower()
                    joint["s0_claim_acc"][0] += s0ok
                    joint["s0_claim_acc"][1] += 1
                    if g["final"][cid] != pv:
                        k1ok = (r1["pred"].get(cid) or "").lower() == g["final"][cid].lower()
                        key = "ch_s0ok" if s0ok else "ch_s0bad"
                        joint[key] += 1
                        joint[key + "_k1ok" if s0ok else "ch_s0bad_k1ok"] += k1ok
            A["decomposition"][m] = dict(joint, s0_claim_accuracy=joint["s0_claim_acc"][0] / max(1, joint["s0_claim_acc"][1]),
                                         P_k1_correct_given_prior_known=joint["ch_s0ok_k1ok"] / max(1, joint["ch_s0ok"]),
                                         P_k1_correct_given_prior_unknown=joint["ch_s0bad_k1ok"] / max(1, joint["ch_s0bad"]))
    json.dump(A, open(os.path.join(V2, f"analysis{out_tag}.json"), "w"), indent=1, default=float)
    return A


if __name__ == "__main__":
    A = main()
    print(json.dumps({k: A[k] for k in ("cells",)}, default=float)[:3000])
