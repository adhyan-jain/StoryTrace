"""Attacker-vs-LLM comparison on EXISTING model outputs (CPU only). Writes results/adv/ADV_RESULTS.json and ADV_RESULTS.md.
 1. ID/OOD gap table: best LLM condition (p2, frozen) vs ledger_lookup and best non-replay attacker, on the LLM subsample.
 2. Error overlap on test_id (item and claim level) between each LLM p2 and the strongest attackers; McNemar exact tests.
 3. Balanced delta sizes: metrics per evidence stratum {irrelevant, contradictory, resolving n=1,2,3} and their macro-average.
 4. Where the story-blind solver fails (needs story?) and whether LLMs do better there.
 5. Transformation drops for attackers (from attacker_results_<tag>.json).
"""
from __future__ import annotations
import json, os
from collections import Counter
import numpy as np
from scipy.stats import binomtest
from ..evaluate import llm_predictions
from ..io import TEST_SPLITS, load_gold, load_task
from ..run import DEFAULT_STORIES, STORIES_PER_SPLIT, pick_stories
from .attackers_adv import Attackers
from .common import ADV, ADV_DATA, evaluate, summary_with_ci

MODELS = ["qwen2.5:7b", "llama3:latest", "qwen3:8b", "mistral:7b"]
NONREPLAY = ["majority_prior", "claim_count_prior", "mention_rule", "positional", "lexical_overlap", "category_then_select",
             "entity_blind", "template_nn", "triple_aware", "ledger_lookup"]
TRANSFORMS = ["identity", "entity_permute_same_pool", "entity_permute_cross_pool", "lexical_paraphrase", "novel_templates",
              "claim_order_random", "story_order_shuffled"]
rng = np.random.default_rng(0)


def stratum(g):
    c = g["meta"]["category"]
    return c if c != "resolving" else f"resolving_n{g['meta']['n_changed']}"


def main():
    A = Attackers()
    R = {"gap": {}, "overlap": {}, "strata": {}, "ledger_failures": {}, "transform_drop": {}}
    att_pred, llm_pred, golds, tasks = {}, {}, {}, {}
    for sp in TEST_SPLITS:
        T, G = load_task(sp), load_gold(sp)
        sub = {t["item_id"] for t in pick_stories(sp, T, STORIES_PER_SPLIT.get(sp, DEFAULT_STORIES))}
        T, G = [t for t in T if t["item_id"] in sub], [g for g in G if g["item_id"] in sub]
        tasks[sp], golds[sp] = T, G
        for n in NONREPLAY + ["always_keep", "symbolic"]:
            att_pred[(n, sp)] = A.predict(n, T, G)
        for m in MODELS:
            llm_pred[(m, sp)] = llm_predictions(m, "p2_explicit_revision", sp, {t["item_id"]: t for t in load_task(sp)})[0]
    # ---------------------------------------------------------------- 1. gap
    for sp in TEST_SPLITS:
        T, G = tasks[sp], golds[sp]
        row = {}
        for n in NONREPLAY + ["always_keep", "symbolic"]:
            row[n] = summary_with_ci(evaluate(att_pred[(n, sp)], T, G), b=300)
        for m in MODELS:
            row[m + "|p2"] = summary_with_ci(evaluate(llm_pred[(m, sp)], T, G), b=300)
        best_att = max(NONREPLAY, key=lambda n: row[n]["label_em"])
        best_llm = max(MODELS, key=lambda m: row[m + "|p2"]["label_em"])
        row["_best_nonreplay_attacker"] = best_att
        row["_best_llm_p2"] = best_llm
        row["_gap_label_em_best_attacker_minus_best_llm"] = row[best_att]["label_em"] - row[best_llm + "|p2"]["label_em"]
        row["_gap_label_em_ledger_lookup_minus_best_llm"] = row["ledger_lookup"]["label_em"] - row[best_llm + "|p2"]["label_em"]
        R["gap"][sp] = row
    # ---------------------------------------------------------------- 2. overlap on test_id
    T, G = tasks["test_id"], golds["test_id"]
    iid = [t["item_id"] for t in T]
    Gd = {g["item_id"]: g for g in G}
    def item_ok(pred):
        ev = evaluate(pred, T, G)
        return np.array([ev["label_ok"][i] for i in iid]), ev
    ok = {n: item_ok(att_pred[(n, "test_id")]) for n in ("ledger_lookup", "positional", "template_nn", "category_then_select", "triple_aware")}
    ok.update({m: item_ok(llm_pred[(m, "test_id")]) for m in MODELS})
    for m in MODELS:
        for n in ("ledger_lookup", "positional", "template_nn", "triple_aware"):
            a, l = ok[n][0], ok[m][0]
            fa, fl = ~a, ~l
            b01, b10 = int((a & fl).sum()), int((fa & l).sum())
            claim_a = np.concatenate([ok[n][1]["claim_err"][i] for i in iid]); claim_l = np.concatenate([ok[m][1]["claim_err"][i] for i in iid])
            R["overlap"][f"{m}|{n}"] = {
                "item_fail_jaccard": float((fa & fl).sum() / max(1, (fa | fl).sum())), "attacker_succeeds_llm_fails": b01, "llm_succeeds_attacker_fails": b10,
                "mcnemar_exact_p": float(binomtest(min(b01, b10), b01 + b10, 0.5).pvalue) if b01 + b10 else 1.0,
                "claim_err_jaccard": float((claim_a & claim_l).sum() / max(1, (claim_a | claim_l).sum())),
                "P(llm_fails|attacker_succeeds)": float(fl[a].mean()) if a.any() else None, "n_both_succeed": int((a & l).sum())}
    # ---------------------------------------------------------------- 3. strata (test_id) with story-cluster bootstrap of macro-average
    strata = sorted({stratum(g) for g in G})
    stories = sorted({g["story_id"] for g in G})
    def strat_rates(okvec):
        d = {s: [] for s in strata}
        for i, o in zip(iid, okvec):
            d[stratum(Gd[i])].append(o)
        return {s: (float(np.mean(v)) if v else np.nan) for s, v in d.items()}
    for n in ("ledger_lookup", "positional", "always_keep", "category_then_select") + tuple(MODELS):
        okvec = (ok[n][0] if n in ok else item_ok(att_pred[(n, "test_id")])[0])
        rates = strat_rates(okvec)
        by_story = {s: [] for s in stories}
        for i, o in zip(iid, okvec):
            by_story[Gd[i]["story_id"]].append((stratum(Gd[i]), o))
        boots = []
        for _ in range(500):
            pick = rng.integers(0, len(stories), len(stories))
            d = {s: [] for s in strata}
            for j in pick:
                for st, o in by_story[stories[j]]:
                    d[st].append(o)
            boots.append(np.nanmean([np.mean(v) for v in d.values() if v]))
        R["strata"][n] = {"label_em_by_stratum": rates, "macro_avg": float(np.nanmean(list(rates.values()))),
                          "macro_avg_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                          "n_by_stratum": dict(Counter(stratum(g) for g in G))}
    # ---------------------------------------------------------------- 4. where the story-blind solver fails
    ll_ok = ok["ledger_lookup"][0]
    fails = [Gd[i] for i, o in zip(iid, ll_ok) if not o]
    R["ledger_failures"] = {"n_fail": len(fails), "n_items": len(iid),
                            "by_category": dict(Counter(g["meta"]["category"] for g in fails)),
                            "by_family": dict(Counter(g["meta"]["evidence_kind"] for g in fails)),
                            "scope_bounded_share": float(np.mean([g["meta"]["scope_bounded"] for g in fails])) if fails else None,
                            "share_of_resolving_items_failed": float(np.mean([not o for i, o in zip(iid, ll_ok) if Gd[i]["meta"]["category"] == "resolving"])),
                            "llm_label_em_on_ledger_failures": {m: float(np.mean([ok[m][0][iid.index(g["item_id"])] for g in fails])) if fails else None for m in MODELS},
                            "llm_label_em_on_ledger_successes": {m: float(np.mean(ok[m][0][ll_ok])) for m in MODELS}}
    # ---------------------------------------------------------------- 5. transformation drops (attackers)
    base = json.load(open(os.path.join(ADV, "attacker_results_identity.json")))
    for tf in TRANSFORMS:
        r = json.load(open(os.path.join(ADV, f"attacker_results_{tf}.json")))
        R["transform_drop"][tf] = {n: {"label_em": v["test_id"]["label_em"], "delta_em": v["test_id"]["delta_exact_match"][0],
                                       "drop_vs_identity": base[n]["test_id"]["label_em"] - v["test_id"]["label_em"], "claim_macro_f1": v["test_id"]["claim_macro_f1"]}
                                   for n, v in r.items() if "test_id" in v}
    json.dump(R, open(os.path.join(ADV, "ADV_RESULTS.json"), "w"), indent=1, default=float)
    # ---------------------------------------------------------------- markdown
    L = ["# Adversarial audit: attacker vs LLM (existing outputs; generated by adv/analyze_adv.py)", "",
         "## 1. ID/OOD: label-exact-match (item) on the LLM subsample, p2 (frozen prompt)", "",
         "| split | " + " | ".join(NONREPLAY[-1:] + ["positional", "template_nn"] + [m.split(":")[0] for m in MODELS]) + " | always_keep | symbolic |", "|---|" + "---|" * 9]
    for sp in TEST_SPLITS:
        r = R["gap"][sp]
        L.append(f"| {sp} | " + " | ".join(f"{r[k]['label_em']:.3f}" for k in ["ledger_lookup", "positional", "template_nn"] + [m + "|p2" for m in MODELS] + ["always_keep", "symbolic"]) + " |")
    L += ["", "## 2. Error overlap on test_id (item level)", "", "| model | attacker | P(LLM fails given attacker succeeds) | attacker ok / LLM fail | LLM ok / attacker fail | McNemar p | item-fail Jaccard | claim-error Jaccard |", "|---|---|---|---|---|---|---|---|"]
    for k, v in R["overlap"].items():
        m, n = k.split("|")
        L.append(f"| {m} | {n} | {v['P(llm_fails|attacker_succeeds)']:.3f} | {v['attacker_succeeds_llm_fails']} | {v['llm_succeeds_attacker_fails']} | {v['mcnemar_exact_p']:.2g} | {v['item_fail_jaccard']:.3f} | {v['claim_err_jaccard']:.3f} |")
    L += ["", "## 3. Balanced delta sizes (label-exact by stratum, test_id; macro-average with story-cluster 95% CI)", "",
          "| system | " + " | ".join(strata) + " | macro-avg [CI] |", "|---|" + "---|" * (len(strata) + 1)]
    for n, v in R["strata"].items():
        L.append(f"| {n} | " + " | ".join(f"{v['label_em_by_stratum'][s]:.3f}" for s in strata) + f" | {v['macro_avg']:.3f} [{v['macro_avg_ci'][0]:.3f}, {v['macro_avg_ci'][1]:.3f}] |")
    L.append(f"\nStratum sizes: {R['strata']['ledger_lookup']['n_by_stratum']}")
    lf = R["ledger_failures"]
    L += ["", "## 4. Where the story-blind ledger solver fails", "", f"- fails {lf['n_fail']}/{lf['n_items']} items; by category {lf['by_category']}; by family {lf['by_family']}",
          f"- share of its failures with temporally bounded scope: {lf['scope_bounded_share']:.2f}; share of resolving items failed: {lf['share_of_resolving_items_failed']:.3f}",
          f"- LLM p2 label-exact on the items it fails: {lf['llm_label_em_on_ledger_failures']}", f"- LLM p2 label-exact on the items it solves: {lf['llm_label_em_on_ledger_successes']}",
          "", "## 5. Attacker label-exact under each transformation (test_id, 50-story subsample; drop vs identity re-realisation)", "",
          "| attacker | " + " | ".join(TRANSFORMS) + " |", "|---|" + "---|" * len(TRANSFORMS)]
    for n in NONREPLAY + ["always_keep", "symbolic", "world_rule_partial:none_ablated"]:
        L.append(f"| {n} | " + " | ".join(f"{R['transform_drop'][t][n]['label_em']:.3f}" for t in TRANSFORMS) + " |")
    open(os.path.join(ADV, "ADV_RESULTS.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
