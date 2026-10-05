"""Builds research/results/baseline_results.json and BASELINE_REPORT.md from raw predictions ONLY (no typed numbers)."""
from __future__ import annotations
import json, os, re, sys
from collections import Counter, defaultdict
import numpy as np
from . import stats
from .evaluate import baseline_predictions, counts_for, llm_predictions, load_raw
from .io import TEST_SPLITS, load_gold, load_task
from .metrics import KEYS, per_story, summarize
from .run import RAW
from .systems import common as C

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
MODELS = ["qwen2.5:7b", "llama3:latest", "qwen3:8b", "mistral:7b"]
DELTA = ["p1_zero_shot_delta", "p2_explicit_revision", "p3_regenerate", "p4_self_consistency"]
NONLLM = ["always_keep", "symbolic"]
HEAD = ["delta_exact_match", "preservation_accuracy", "revision_recall", "revision_precision", "collateral_claim_rate", "conflict_recall"]
CONTRASTS = [("p2_explicit_revision", "p1_zero_shot_delta"), ("p3_regenerate", "p1_zero_shot_delta"), ("p4_self_consistency", "p2_explicit_revision")]
CONTRAST_METRICS = ["delta_exact_match", "preservation_accuracy", "revision_recall"]
B = int(os.environ.get("SSR_BOOT", 4000))


def fmt(v, d=3):
    return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"


def ci_str(M, name):
    est, lo, hi = stats.boot_ci(M, name, b=B)
    return f"{fmt(est)} [{fmt(lo)}, {fmt(hi)}]"


def claim_records(preds, split):
    """Per-claim error taxonomy rows for one prediction set."""
    tasks = {t["item_id"]: t for t in load_task(split)}
    gold = {g["item_id"]: g for g in load_gold(split)}
    tax = Counter()
    for iid, p in preds.items():
        t, g = tasks[iid], gold[iid]
        evday = g["meta"]["evidence_slot"]
        ents = {x for x in re.findall(r"[A-Z][a-z]+|(?<=the )[a-z]+ [a-z]+", t["evidence"])} | set(re.findall(r"\b[a-z]+ [a-z]+\b", t["evidence"]))
        for c in t["claims"]:
            gl, gv = g["labels"][c["id"]]["label"], C.norm(g["labels"][c["id"]]["value"])
            pl, pv = p.get(c["id"], ("INVALID", ""))
            mentioned = re.search(rf"\b{re.escape(c['entity'])}\b", t["evidence"]) is not None
            tax["claims"] += 1
            if pl == "INVALID":
                tax["invalid"] += 1
            if gl == "REVISE":
                tax["gold_revise"] += 1
                if pl == "KEEP": tax["missed_revision"] += 1
                elif pl == "CONFLICT": tax["revise_called_conflict"] += 1
                elif pl == "REVISE" and pv != gv: tax["wrong_value_revision"] += 1
                if c["attr"] == "proploc" and pl != "REVISE": tax["missed_dependent_claim"] += 1
            if gl == "KEEP":
                tax["gold_keep"] += 1
                if pl == "REVISE":
                    tax["collateral_revision"] += 1
                    tax["collateral_revision_mentioned_entity" if mentioned else "collateral_revision_unmentioned_entity"] += 1
                    if c["slot"] < evday and g["meta"]["evidence_kind"] != "assertion": tax["temporal_leakage_into_past"] += 1
                if pl == "CONFLICT": tax["false_contradiction_on_keep"] += 1
            if gl == "CONFLICT":
                tax["gold_conflict"] += 1
                if pl == "KEEP": tax["missed_contradiction"] += 1
                elif pl == "REVISE": tax["conflict_called_revise"] += 1
            if pl == "CONFLICT" and gl != "CONFLICT":
                tax["false_contradiction_total"] += 1
    return dict(tax)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {"cfg": {"bootstrap": B, "models": MODELS}, "metrics": {}, "by_category": {}, "subgroups": {}, "contrasts": {}, "qa": {}, "taxonomy": {}, "cost": {}, "criteria": {}}
    SM = {}  # (model, system, split) -> (story_ids, M)

    def put(model, system, split, preds):
        c, gold = counts_for(preds, split)
        sids, M = per_story(c, gold)
        SM[(model, system, split)] = (sids, M, c, gold)
        res["metrics"].setdefault(model, {}).setdefault(system, {})[split] = {k: (None if v is None else float(v)) for k, v in summarize(M.sum(0)).items()}
        res["metrics"][model][system][split]["n_stories"] = len(sids)
        for h in HEAD:
            e, lo, hi = stats.boot_ci(M, h, b=B)
            res["metrics"][model][system][split][h + "_ci"] = [None if np.isnan(x) else float(x) for x in (e, lo, hi)]

    for split in TEST_SPLITS:
        for nl in NONLLM:
            put("non-LLM", nl, split, baseline_predictions(nl, split))
    put("non-LLM", "symbolic_privileged_grammar", "test_ood_lex", baseline_predictions("symbolic_privileged_grammar", "test_ood_lex"))
    answers = {}
    for m in MODELS:
        for s in DELTA:
            for split in TEST_SPLITS:
                tasks = {t["item_id"]: t for t in load_task(split)}
                preds, _ = llm_predictions(m, s, split, tasks)
                if preds:
                    put(m, s, split, preds)
        for split in TEST_SPLITS:
            tasks = {t["item_id"]: t for t in load_task(split)}
            _, ans = llm_predictions(m, "p5_direct_qa", split, tasks)
            if ans:
                answers[(m, split)] = ans
        for s in DELTA + ["p5_direct_qa"]:
            rows = load_raw(m, s)
            if rows:
                res["cost"].setdefault(m, {})[s] = {"calls": len(rows), "mean_prompt_tokens": float(np.mean([r["prompt_tokens"] or 0 for r in rows])),
                                                   "mean_completion_tokens": float(np.mean([r["completion_tokens"] or 0 for r in rows])),
                                                   "total_wall_s": float(sum(r["wall_s"] or 0 for r in rows)), "errors": sum(bool(r["error"]) for r in rows)}

    # ---- by category / subgroup on test_id (per item counts re-aggregated)
    for (m, s, split), (sids, M, c, gold) in SM.items():
        if split != "test_id":
            continue
        for name, pred_fn in (("category", lambda g: g["meta"]["category"]),
                              ("temporal", lambda g: "bounded" if g["meta"]["scope_bounded"] else ("unbounded" if g["meta"]["category"] == "resolving" else None)),
                              ("dependent", lambda g: ("has_dependent" if g["meta"]["has_dependent_change"] else "no_dependent") if g["meta"]["category"] == "resolving" else None),
                              ("evidence_kind", lambda g: g["meta"]["evidence_kind"]), ("n_changed", lambda g: str(g["meta"]["n_changed"]) if g["meta"]["category"] == "resolving" else None)):
            groups = defaultdict(lambda: np.zeros(len(KEYS)))
            for iid, v in c.items():
                k = pred_fn(gold[iid])
                if k:
                    groups[k] += v
            res["subgroups"].setdefault(name, {}).setdefault(m, {})[s] = {k: {kk: (None if vv is None else float(vv)) for kk, vv in summarize(v).items() if kk in HEAD + ["n_items"]} for k, v in sorted(groups.items())}

    # ---- pre-declared paired contrasts (test_id), Holm per model
    for m in MODELS:
        fam = {}
        for a, b in CONTRASTS:
            if (m, a, "test_id") in SM and (m, b, "test_id") in SM:
                sa, Ma, *_ = SM[(m, a, "test_id")]; sb, Mb, *_ = SM[(m, b, "test_id")]
                common = sorted(set(sa) & set(sb))
                ia, ib = [sa.index(x) for x in common], [sb.index(x) for x in common]
                for met in CONTRAST_METRICS:
                    d = stats.paired_diff(Ma[ia], Mb[ib], met, b=B)
                    pa = summarize(Ma[ia].sum(0))[met]; pb = summarize(Mb[ib].sum(0))[met]
                    d["cohens_h"] = float(stats.cohens_h(pa, pb)) if pa is not None and pb is not None else None
                    fam[f"{a} - {b} | {met}"] = d
        hp = stats.holm({k: v["p_perm"] for k, v in fam.items()})
        for k in fam:
            fam[k]["p_holm"] = hp[k]
        res["contrasts"][m] = {k: {kk: float(vv) if vv is not None else None for kk, vv in v.items()} for k, v in fam.items()}

    # ---- final-answer vs state-delta (test_id + all splits pooled)
    for m in MODELS:
        for s in DELTA:
            tot = Counter()
            for split in TEST_SPLITS:
                if (m, s, split) not in SM:
                    continue
                _, _, c, gold = SM[(m, s, split)]
                tasks = {t["item_id"]: t for t in load_task(split)}
                preds, _ = llm_predictions(m, s, split, tasks)
                for iid, p in preds.items():
                    t, g = tasks[iid], gold[iid]
                    pid = t["probe"]["claim_id"]
                    claim = next(x for x in t["claims"] if x["id"] == pid)
                    pl, pv = p[pid]
                    qa = C.norm(claim["value"]) if pl in ("KEEP", "CONFLICT") else pv
                    qa_ok = qa == C.norm(g["probe_answer"])
                    exact = bool(c[iid][KEYS.index("exact_items")])
                    coll = bool(c[iid][KEYS.index("collateral_items")])
                    sp = "id" if split == "test_id" else "ood"
                    for tag in (sp, "all"):
                        tot[f"{tag}_items"] += 1
                        tot[f"{tag}_qa_from_delta_ok"] += qa_ok
                        tot[f"{tag}_delta_exact"] += exact
                        tot[f"{tag}_qa_ok_and_delta_wrong"] += qa_ok and not exact
                        tot[f"{tag}_qa_ok_and_collateral"] += qa_ok and coll
                        tot[f"{tag}_qa_ok_and_missed_or_wrong"] += qa_ok and not exact and not coll
            if tot:
                res["qa"].setdefault(m, {})[s] = dict(tot)
        for split in TEST_SPLITS:
            if (m, split) in answers:
                gold = {g["item_id"]: g for g in load_gold(split)}
                a = answers[(m, split)]
                res["qa"].setdefault(m, {}).setdefault("p5_direct_qa", {})[split] = {"items": len(a), "acc": float(np.mean([a[i] == C.norm(gold[i]["probe_answer"]) for i in a]))}

    # ---- error taxonomy (all splits pooled, and test_id)
    for m in MODELS:
        for s in DELTA:
            for scope, splits in (("test_id", ["test_id"]), ("all_test", TEST_SPLITS)):
                tot = Counter()
                for split in splits:
                    if (m, s, split) in SM:
                        tasks = {t["item_id"]: t for t in load_task(split)}
                        preds, _ = llm_predictions(m, s, split, tasks)
                        tot.update(claim_records(preds, split))
                if tot:
                    res["taxonomy"].setdefault(m, {}).setdefault(s, {})[scope] = dict(tot)

    # ---- pre-registered failure criterion (test_id, greedy delta conditions)
    for m in MODELS:
        for s in DELTA:
            k = res["metrics"].get(m, {}).get(s, {}).get("test_id")
            if not k:
                continue
            pres_hi, rec_hi = k["preservation_accuracy_ci"][2], k["revision_recall_ci"][2]
            res["criteria"].setdefault(m, {})[s] = {"preservation_ci_upper": pres_hi, "recall_ci_upper": rec_hi,
                                                   "criterion_1_met": bool((pres_hi is not None and pres_hi < 0.97) or (rec_hi is not None and rec_hi < 0.85)),
                                                   "delta_em": k["delta_exact_match"]}
    json.dump(res, open(os.path.join(OUT, "baseline_results.json"), "w"), indent=1, default=float)
    write_report(res)


def write_report(res):
    L = ["# SSR-Bench baseline report (generated by research/ssr_bench/analyze.py — no hand-typed numbers)", "",
         f"Bootstrap: {res['cfg']['bootstrap']} cluster resamples over STORIES (3 matched items each). Intervals are 95% percentile CIs.", ""]
    L += ["## 1. Test-ID headline metrics (value-aware, per-claim; 10 claims/item)", "", "| model | system | n items | delta EM | preservation | revision recall | revision precision | collateral claim rate | conflict recall |", "|---|---|---|---|---|---|---|---|---|"]
    for m, sysd in res["metrics"].items():
        for s, sp in sysd.items():
            if "test_id" in sp:
                k = sp["test_id"]
                L.append(f"| {m} | {s} | {int(k['n_items'])} | " + " | ".join(f"{fmt(k[h + '_ci'][0])} [{fmt(k[h + '_ci'][1])}, {fmt(k[h + '_ci'][2])}]" for h in HEAD) + " |")
    L += ["", "## 2. All splits: delta exact match / preservation / revision recall (point estimates; CIs in baseline_results.json)", "",
          "| model | system | " + " | ".join(TEST_SPLITS) + " |", "|---|---|" + "---|" * len(TEST_SPLITS)]
    for m, sysd in res["metrics"].items():
        for s, sp in sysd.items():
            L.append(f"| {m} | {s} | " + " | ".join((f"{fmt(sp[x]['delta_exact_match'],2)} / {fmt(sp[x]['preservation_accuracy'],2)} / {fmt(sp[x]['revision_recall'],2)}" if x in sp else "—") for x in TEST_SPLITS) + " |")
    L += ["", "## 3. By evidence category (test_id): preservation / revision recall / conflict recall / delta EM", "", "| model | system | resolving | irrelevant | contradictory |", "|---|---|---|---|---|"]
    for m, d in res["subgroups"].get("category", {}).items():
        for s, g in d.items():
            f = lambda k: f"pres {fmt(g[k]['preservation_accuracy'],2)} · rec {fmt(g[k]['revision_recall'],2)} · conf {fmt(g[k]['conflict_recall'],2)} · EM {fmt(g[k]['delta_exact_match'],2)}" if k in g else "—"
            L.append(f"| {m} | {s} | {f('resolving')} | {f('irrelevant')} | {f('contradictory')} |")
    for name, title in (("temporal", "temporal scope (resolving items): bounded vs unbounded change"), ("dependent", "dependent-claim changes (resolving items)"), ("n_changed", "number of claims that must change (resolving items)")):
        L += ["", f"## 4.{name}. {title}: revision recall / preservation / delta EM", ""]
        keys = sorted({k for d in res["subgroups"].get(name, {}).values() for g in d.values() for k in g})
        L += ["| model | system | " + " | ".join(keys) + " |", "|---|---|" + "---|" * len(keys)]
        for m, d in res["subgroups"].get(name, {}).items():
            for s, g in d.items():
                L.append(f"| {m} | {s} | " + " | ".join((f"rec {fmt(g[k]['revision_recall'],2)} · pres {fmt(g[k]['preservation_accuracy'],2)} · EM {fmt(g[k]['delta_exact_match'],2)} (n={int(g[k]['n_items'])})" if k in g else "—") for k in keys) + " |")
    L += ["", "## 5. Pre-declared paired contrasts on test_id (cluster-bootstrap CI, sign-flip permutation p, Holm within model)", "",
          "| model | contrast | metric | diff | 95% CI | Cohen's h | p (perm) | p (Holm) | stories |", "|---|---|---|---|---|---|---|---|---|"]
    for m, d in res["contrasts"].items():
        for k, v in d.items():
            c, met = k.split(" | ")
            L.append(f"| {m} | {c} | {met} | {fmt(v['diff'])} | [{fmt(v['ci_lo'])}, {fmt(v['ci_hi'])}] | {fmt(v['cohens_h'])} | {fmt(v['p_perm'],4)} | {fmt(v['p_holm'],4)} | {int(v['n_stories'])} |")
    L += ["", "## 6. Final-answer correctness vs state-delta correctness", "",
          "`QA from delta` = the value the model's delta implies for the probed claim (REVISE→new value; KEEP/CONFLICT→prior value). Illusion = QA correct while the delta is not exactly right.", "",
          "| model | system | scope | items | QA-from-delta acc | delta EM | QA correct but delta wrong (share of QA-correct) | …of which collateral revision on a KEEP claim |", "|---|---|---|---|---|---|---|---|"]
    for m, d in res["qa"].items():
        for s, v in d.items():
            if s == "p5_direct_qa":
                continue
            for sc in ("id", "ood", "all"):
                if f"{sc}_items" in v and v[f"{sc}_items"]:
                    n = v[f"{sc}_items"]; ok = v[f"{sc}_qa_from_delta_ok"]
                    L.append(f"| {m} | {s} | {sc} | {int(n)} | {fmt(ok / n)} | {fmt(v[f'{sc}_delta_exact'] / n)} | {fmt(v[f'{sc}_qa_ok_and_delta_wrong'] / ok) if ok else 'n/a'} ({int(v[f'{sc}_qa_ok_and_delta_wrong'])}/{int(ok)}) | {int(v[f'{sc}_qa_ok_and_collateral'])} |")
    L += ["", "Direct single-answer QA (p5, no ledger; probe question only):", "", "| model | " + " | ".join(TEST_SPLITS) + " |", "|---|" + "---|" * len(TEST_SPLITS)]
    for m, d in res["qa"].items():
        if "p5_direct_qa" in d:
            L.append(f"| {m} | " + " | ".join((fmt(d["p5_direct_qa"][x]["acc"], 2) if x in d["p5_direct_qa"] else "—") for x in TEST_SPLITS) + " |")
    L += ["", "## 7. Error taxonomy (claim-level counts, all test splits pooled)", "", "| model | system | claims | missed revision | wrong-value revision | missed dependent claim | collateral revision | …on mentioned entity | …on unmentioned entity | temporal leakage into past | missed contradiction | false contradiction | invalid |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, d in res["taxonomy"].items():
        for s, v in d.items():
            t = v.get("all_test", {})
            g = lambda k: int(t.get(k, 0))
            L.append(f"| {m} | {s} | {g('claims')} | {g('missed_revision')}/{g('gold_revise')} | {g('wrong_value_revision')} | {g('missed_dependent_claim')} | {g('collateral_revision')}/{g('gold_keep')} | {g('collateral_revision_mentioned_entity')} | {g('collateral_revision_unmentioned_entity')} | {g('temporal_leakage_into_past')} | {g('missed_contradiction')}/{g('gold_conflict')} | {g('false_contradiction_total')} | {g('invalid')} |")
    L += ["", "Not measured (and therefore not claimed): over-/under-confidence (no confidences elicited); evidence misattribution beyond the mentioned/unmentioned-entity split.", "",
          "## 8. Pre-registered failure criterion 1 (test_id)", "", "| model | system | delta EM | preservation CI upper | recall CI upper | criterion 1 met |", "|---|---|---|---|---|---|"]
    for m, d in res["criteria"].items():
        for s, v in d.items():
            L.append(f"| {m} | {s} | {fmt(v['delta_em'])} | {fmt(v['preservation_ci_upper'])} | {fmt(v['recall_ci_upper'])} | {v['criterion_1_met']} |")
    L += ["", "## 9. Cost (all calls so far)", "", "| model | system | calls | mean prompt tok | mean completion tok | total wall (h) | errors |", "|---|---|---|---|---|---|---|"]
    for m, d in res["cost"].items():
        for s, v in d.items():
            L.append(f"| {m} | {s} | {v['calls']} | {v['mean_prompt_tokens']:.0f} | {v['mean_completion_tokens']:.0f} | {v['total_wall_s'] / 3600:.2f} | {v['errors']} |")
    open(os.path.join(OUT, "BASELINE_REPORT.md"), "w").write("\n".join(L) + "\n")
    print("wrote BASELINE_REPORT.md")


if __name__ == "__main__":
    main()
