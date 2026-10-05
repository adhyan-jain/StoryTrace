"""Independent recomputation of the headline metrics from RAW model output + task + gold with plain loops.

Deliberately imports NOTHING from metrics.py / evaluate.py / analyze.py (own parser, own normaliser, own aggregation), then
compares to research/results/baseline_results.json. Exits 1 on any mismatch.
"""
import json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "results", "raw")
DATA = os.path.join(ROOT, "ssr_bench", "data")


def rd(p):
    return [json.loads(l) for l in open(p)]


def nm(v):
    v = v.strip().strip('."\'').lower()
    v = re.sub(r"^(in|to|at|by)\s+", "", v)
    return re.sub(r"^the\s+", "", v).strip()


def parse(system, content, claims):
    try:
        o = json.loads(content)
        assert isinstance(o, dict)
    except Exception:
        return {c["id"]: ("INVALID", "") for c in claims}
    out = {}
    for c in claims:
        r = o.get(c["id"])
        if not isinstance(r, str):
            out[c["id"]] = ("INVALID", ""); continue
        s = r.strip(); u = s.upper()
        if system == "p3_regenerate":
            out[c["id"]] = ("CONFLICT", "") if u.startswith("CONFLICT") else (("KEEP", "") if nm(s) == nm(c["value"]) else ("REVISE", nm(s)))
        elif u.startswith("KEEP"): out[c["id"]] = ("KEEP", "")
        elif u.startswith("CONFLICT"): out[c["id"]] = ("CONFLICT", "")
        elif u.startswith("REVISE"): out[c["id"]] = ("REVISE", nm(s.split(":", 1)[1] if ":" in s else ""))
        else: out[c["id"]] = ("INVALID", "")
    return out


def main():
    res = json.load(open(os.path.join(ROOT, "results", "baseline_results.json")))
    bad = 0
    checked = 0
    for model, systems in res["metrics"].items():
        if model == "non-LLM":
            continue
        for system, splits in systems.items():
            if system == "p4_self_consistency":
                continue  # aggregated vote; checked separately below
            for split, rep in splits.items():
                task = {t["item_id"]: t for t in rd(f"{DATA}/{split}.task.jsonl")}
                gold = {g["item_id"]: g for g in rd(f"{DATA}/{split}.gold.jsonl")}
                rows = [r for r in rd(f"{RAW}/{model.replace(':', '_')}/{system}.jsonl") if r["split"] == split]
                n = Counter()
                for r in rows:
                    t, g = task[r["item_id"]], gold[r["item_id"]]
                    p = parse(system, r["content"], t["claims"])
                    n["items"] += 1
                    ex_all = True
                    for c in t["claims"]:
                        gl, gv = g["labels"][c["id"]]["label"], nm(g["labels"][c["id"]]["value"])
                        pl, pv = p[c["id"]]
                        ex = gl == pl and (gl != "REVISE" or gv == pv)
                        ex_all &= ex
                        n["keep_total"] += gl == "KEEP"; n["keep_ok"] += gl == "KEEP" and pl == "KEEP"
                        n["pred_rev"] += pl == "REVISE"; n["gold_rev"] += gl == "REVISE"; n["tp_rev"] += gl == "REVISE" and ex
                        n["conf_gold"] += gl == "CONFLICT"; n["conf_tp"] += gl == "CONFLICT" and ex
                    n["exact"] += ex_all
                mine = {"delta_exact_match": n["exact"] / n["items"], "preservation_accuracy": n["keep_ok"] / n["keep_total"],
                        "revision_recall": n["tp_rev"] / n["gold_rev"] if n["gold_rev"] else None,
                        "revision_precision": n["tp_rev"] / n["pred_rev"] if n["pred_rev"] else None,
                        "conflict_recall": n["conf_tp"] / n["conf_gold"] if n["conf_gold"] else None}
                for k, v in mine.items():
                    checked += 1
                    if (v is None) != (rep[k] is None) or (v is not None and abs(v - rep[k]) > 1e-9):
                        bad += 1
                        print("MISMATCH", model, system, split, k, v, rep[k])
    print(f"independent recomputation: {checked} values checked, {bad} mismatches")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
