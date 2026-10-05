"""Leakage / integrity gates (thresholds fixed in research/PREREGISTRATION.md before any result was seen).

Run:  python -m research.ssr_bench.leakage   -> writes research/results/leakage_report.json, exits 1 on any failed gate.
"""
from __future__ import annotations
import json, os, re, sys
from collections import Counter
import numpy as np
from scipy.stats import chi2_contingency
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from scipy.sparse import csr_matrix, hstack
from . import lexicon as lx, oracle_a, oracle_b
from .generate import SPLITS, sig_is_ood
from .io import TEST_SPLITS, load_gold, load_task
from .world import Assertion, Event, Story

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
THR = {"G1": 0.60, "G2": 0.40, "G3": 0.70, "G4_p": 0.01, "G6": 0.95}
ALLOWED_TASK_KEYS = {"item_id", "story", "evidence", "claims", "probe"}
ALLOWED_CLAIM_KEYS = {"id", "entity", "attr", "slot", "value", "statement"}
FORBIDDEN_WORDS = ["RESOLVING", "IRRELEVANT", "CONTRADICTORY", "KEEP", "REVISE", "CONFLICT", "INVALIDATE"]
CATS = ["resolving", "irrelevant", "contradictory"]


def story_from_world(w) -> tuple[Story, object]:
    ev = dict(w["evidence"])
    typ = ev.pop("type")
    evidence = Assertion(**ev) if typ == "Assertion" else Event(**ev)
    st = Story(w["chars"], w["props"], w["locs"], w["init_loc"], w["init_holder"], w["init_proploc"],
               frozenset(w["init_injured"]), [Event(**e) for e in w["events"]], w["n_slots"])
    return st, evidence


# ------------------------------------------------------------------ G8
def g8_oracles(split):
    gold = load_gold(split)
    task = {t["item_id"]: t for t in load_task(split)}
    bad = 0
    for g in gold:
        st, ev = story_from_world(g["world"])
        keys = [(c["attr"], c["entity"], c["slot"]) for c in task[g["item_id"]]["claims"]]
        ids = [c["id"] for c in task[g["item_id"]]["claims"]]
        ga, gb = oracle_a.gold(st, ev, keys), oracle_b.gold(st, ev, keys)
        want = {k: (g["labels"][i]["label"], g["labels"][i]["value"]) for k, i in zip(keys, ids)}
        bad += not (ga == gb == want)
    return {"items": len(gold), "disagreements": bad}


# ------------------------------------------------------------------ G5
def g5_exposure():
    problems = []
    for sp in SPLITS:
        raw = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"{sp}.task.jsonl")).read()
        for w in FORBIDDEN_WORDS:
            if re.search(rf"\b{w}\b", raw, re.I):
                problems.append((sp, "forbidden word", w))
        for t in load_task(sp):
            if set(t) != ALLOWED_TASK_KEYS:
                problems.append((sp, "task keys", sorted(t)))
            if any(set(c) != ALLOWED_CLAIM_KEYS for c in t["claims"]):
                problems.append((sp, "claim keys", ""))
    return problems


# ------------------------------------------------------------------ delexicalisation
_ALL = sorted(set(lx.CHARS_A + lx.CHARS_B + lx.CHARS_NEAR), key=len, reverse=True)
_PROPS = sorted(set(lx.PROPS_A + lx.PROPS_B + lx.PROPS_NEAR), key=len, reverse=True)
_LOCS = sorted(set(lx.LOCS_A + lx.LOCS_B + lx.LOCS_NEAR), key=len, reverse=True)


def delex(s: str) -> str:
    for lst, tok in ((_PROPS, "<P>"), (_LOCS, "<L>"), (_ALL, "<C>")):
        for x in lst:
            s = re.sub(rf"\b{re.escape(x)}\b", tok, s)
    return re.sub(r"\d+", "N", s)


# ------------------------------------------------------------------ G6 distinctness
def g6_distinct(split):
    T, G = load_task(split), load_gold(split)
    items = set()
    for t, g in zip(T, G):
        pat = tuple(sorted((c["attr"], g["labels"][c["id"]]["label"]) for c in t["claims"]))
        items.add((tuple(delex(s) for s in t["story"]), delex(t["evidence"]), pat))
    ev_t = {delex(t["evidence"]) for t in T}
    return {"items": len(T), "unique_delex_items": len(items), "ratio": len(items) / len(T), "unique_evidence_templates": len(ev_t)}


# ------------------------------------------------------------------ G7 disjointness
def sent_templates(split):
    out = set()
    for t in load_task(split):
        out |= {delex(re.sub(r"^(At the start,|On day \d+,|Day \d+:|During day \d+,|By the end of day \d+,|As day \d+ unfolded,)\s*", "", s))
                for s in t["story"][1:] if not s.startswith("At the start")}
        out.add(delex(re.sub(r"^(On day \d+,|Day \d+:|During day \d+,|By the end of day \d+,|As day \d+ unfolded,)\s*", "", t["evidence"])))
    return out


def g7_disjoint():
    res = {}
    id_sets = set().union(*(sent_templates(s) for s in ("train", "dev", "test_id")))
    ood_t = sent_templates("test_ood_lex")
    res["ood_lex_template_overlap_with_train_dev_id"] = sorted(ood_t & id_sets)
    ent_pool = set(lx.CHARS_A + lx.PROPS_A + lx.LOCS_A)
    raw = " ".join(" ".join(t["story"]) + t["evidence"] for t in load_task("test_ood_ent"))
    res["ood_ent_uses_A_pool_entities"] = sorted(e for e in ent_pool if re.search(rf"\b{re.escape(e)}\b", raw))
    id_sigs = {tuple(g["meta"]["signature"]) for s in ("train", "dev", "test_id") for g in load_gold(s)}
    ood_sigs = {tuple(g["meta"]["signature"]) for g in load_gold("test_ood_struct")}
    res["ood_struct_signature_overlap"] = sorted("|".join(x) for x in id_sigs & ood_sigs)
    res["id_sigs_flagged_ood"] = sum(sig_is_ood(s) for s in id_sigs)
    res["n_id_signatures"], res["n_ood_signatures"] = len(id_sigs), len(ood_sigs)
    # held-out *marker* templates too
    res["marker_heldout_in_id"] = sorted({m for t in load_task("train") for m in re.findall(r"By the end of day|As day \d+ unfolded", " ".join(t["story"]) + t["evidence"])})
    return res


# ------------------------------------------------------------------ shallow attackers
def meta_feats(t):
    e = t["evidence"]
    slot = int(re.search(r"\d+", e).group())
    return [len(e), len(e.split()), e.count(","), e.count(":"), e.count("."), slot,
            len(t["story"]), sum(map(len, t["story"]))]


def cat_of(g):
    return g["meta"]["category"]


def best_f1(models, Xtr, ytr, Xte, yte, **kw):
    best = 0.0
    for m in models:
        m.fit(Xtr, ytr)
        best = max(best, f1_score(yte, m.predict(Xte), **kw))
    return best


def g1_g2(test_splits):
    Ttr, Gtr = load_task("train"), load_gold("train")
    ytr = [cat_of(g) for g in Gtr]
    vec = CountVectorizer(ngram_range=(1, 2), min_df=2)
    Xtr = vec.fit_transform([delex(t["evidence"]) for t in Ttr])
    Mtr = np.array([meta_feats(t) for t in Ttr], dtype=float)
    out = {}
    for sp in test_splits:
        T, G = load_task(sp), load_gold(sp)
        y = [cat_of(g) for g in G]
        Xte = vec.transform([delex(t["evidence"]) for t in T])
        Mte = np.array([meta_feats(t) for t in T], dtype=float)
        g1 = best_f1([LogisticRegression(max_iter=3000), RandomForestClassifier(300, random_state=0)], Xtr, ytr, Xte, y, average="macro")
        g2 = best_f1([RandomForestClassifier(300, random_state=0), GradientBoostingClassifier(random_state=0)], Mtr, ytr, Mte, y, average="macro")
        out[sp] = {"G1_text_only_macroF1": round(g1, 4), "G2_meta_only_macroF1": round(g2, 4)}
    return out


def claim_rows(split):
    T, G = load_task(split), load_gold(split)
    rows, y = [], []
    texts = []
    for t, g in zip(T, G):
        e = t["evidence"]
        evslot = g["meta"]["evidence_slot"]
        for i, c in enumerate(t["claims"]):
            ment = int(re.search(rf"\b{re.escape(c['entity'])}\b", e) is not None) + (
                int(c["attr"] == "holder" and re.search(rf"\b{re.escape(c['value'])}\b", e) is not None))
            rows.append([c["slot"] - evslot, int(c["slot"] >= evslot), int(c["slot"] == evslot), int(c["slot"] == evslot - 1), ment, i,
                         ["loc", "holder", "proploc", "injured"].index(c["attr"]), int(c["slot"] > evslot)])
            y.append(int(g["labels"][c["id"]]["label"] != "KEEP"))
            texts.append(delex(e))
    return np.array(rows, dtype=float), np.array(y), texts


def g3_g4(test_splits):
    Xtr, ytr, txt = claim_rows("train")
    vec = CountVectorizer(ngram_range=(1, 2), min_df=2)
    Str = hstack([csr_matrix(Xtr), vec.fit_transform(txt)]).tocsr()
    out = {}
    for sp in test_splits:
        X, y, tx = claim_rows(sp)
        S = hstack([csr_matrix(X), vec.transform(tx)]).tocsr()
        f_lr = best_f1([LogisticRegression(max_iter=5000, class_weight="balanced")], Str, ytr, S, y)
        f_gb = best_f1([GradientBoostingClassifier(random_state=0)], Xtr, ytr, X, y)
        rule = ((X[:, 4] > 0) & (X[:, 1] > 0)).astype(int)  # "mentioned entity and slot >= evidence slot"
        out[sp] = {"G3_claim_changed_F1_best_shallow": round(max(f_lr, f_gb), 4), "rule_mention_and_after_F1": round(f1_score(y, rule), 4),
                   "positive_rate": round(float(y.mean()), 4)}
    X, y, _ = claim_rows("test_id")
    ct = np.zeros((10, 2))
    for p, yy in zip(X[:, 5].astype(int), y):
        ct[p, yy] += 1
    out["G4_position_chi2_p"] = float(chi2_contingency(ct + 1e-9)[1])
    return out


def cue_words():
    T, G = load_task("train"), load_gold("train")
    vec = CountVectorizer(ngram_range=(1, 1), min_df=5)
    X = vec.fit_transform([delex(t["evidence"]) for t in T])
    m = LogisticRegression(max_iter=3000).fit(X, [cat_of(g) for g in G])
    names = np.array(vec.get_feature_names_out())
    return {c: names[np.argsort(-m.coef_[i])[:6]].tolist() for i, c in enumerate(m.classes_)}


def main():
    os.makedirs(OUT, exist_ok=True)
    rep, ok = {}, True
    rep["G5_exposure_problems"] = g5_exposure(); ok &= not rep["G5_exposure_problems"]
    rep["G6_distinct"] = {sp: g6_distinct(sp) for sp in SPLITS}; ok &= all(v["ratio"] >= THR["G6"] for v in rep["G6_distinct"].values())
    rep["G7_disjoint"] = g7_disjoint()
    d = rep["G7_disjoint"]
    ok &= not (d["ood_lex_template_overlap_with_train_dev_id"] or d["ood_ent_uses_A_pool_entities"] or d["ood_struct_signature_overlap"]
               or d["id_sigs_flagged_ood"] or d["marker_heldout_in_id"])
    rep["G8_oracles"] = {sp: g8_oracles(sp) for sp in SPLITS}; ok &= all(v["disagreements"] == 0 for v in rep["G8_oracles"].values())
    rep["G1_G2"] = g1_g2(TEST_SPLITS)
    ok &= all(v["G1_text_only_macroF1"] <= THR["G1"] and v["G2_meta_only_macroF1"] <= THR["G2"] for v in rep["G1_G2"].values())
    rep["G3_G4"] = g3_g4(TEST_SPLITS)
    ok &= all(v["G3_claim_changed_F1_best_shallow"] <= THR["G3"] for k, v in rep["G3_G4"].items() if k.startswith("test"))
    ok &= rep["G3_G4"]["G4_position_chi2_p"] > THR["G4_p"]
    rep["cue_words_text_only_top"] = cue_words()
    rep["thresholds"] = THR
    rep["ALL_GATES_PASS"] = bool(ok)
    with open(os.path.join(OUT, "leakage_report.json"), "w") as f:
        json.dump(rep, f, indent=2, default=str)
    print(json.dumps({k: rep[k] for k in ("G1_G2", "G3_G4", "cue_words_text_only_top", "ALL_GATES_PASS")}, indent=1, default=str))
    print("G5", rep["G5_exposure_problems"]); print("G7", json.dumps(rep["G7_disjoint"], default=str)[:600])
    print("G6 min ratio", min(v["ratio"] for v in rep["G6_distinct"].values()), "G8 disagreements", sum(v["disagreements"] for v in rep["G8_oracles"].values()))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
