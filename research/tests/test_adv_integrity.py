"""Integrity tests for the adversarial audit (Addendum C): benchmark untouched, attackers isolated, scorers sane."""
import ast, hashlib, json, os
import pytest
from research.ssr_bench import lexicon as lx
from research.ssr_bench.adv import novel_realize as NR
from research.ssr_bench.adv.attackers_adv import Attackers
from research.ssr_bench.adv.common import ADV_DATA
from research.ssr_bench.adv.scoring_audit import conflict_set, score_item
from research.ssr_bench.io import load_gold, load_task

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSR = os.path.join(ROOT, "ssr_bench")
SNAP = os.path.join(ROOT, "results", "snapshot_2026-10-02", "BENCHMARK_HASHES.txt")


def test_benchmark_definition_and_data_unchanged_since_audit_start():
    for line in open(SNAP):
        digest, path = line.split()
        assert hashlib.sha256(open(os.path.join(SSR, path), "rb").read()).hexdigest() == digest, f"{path} changed"


def test_novel_templates_disjoint_from_all_existing_templates():
    existing = set()
    for tbl in (lx.EVENT_TPL, lx.ASSERT_TPL):
        for pools in tbl.values():
            for p in pools:
                existing.update(p)
    for pools in (lx.MARKERS,):
        for p in pools:
            existing.update(p)
    assert not (set(NR.all_templates()) & existing)


def test_adv_attackers_do_not_import_oracles_or_generator():
    for fn in ("attackers_adv.py", "symbolic_ablate.py"):
        tree = ast.parse(open(os.path.join(SSR, "adv", fn)).read())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                mods.add((n.module or "").split(".")[-1])
                mods.update(a.name for a in n.names)
            elif isinstance(n, ast.Import):
                mods.update(a.name.split(".")[-1] for a in n.names)
        assert not ({"oracle_a", "oracle_b", "generate"} & mods), fn


def test_ledger_lookup_never_reads_the_story():
    for t in load_task("test_id")[:60]:
        a = Attackers.ledger_lookup(t)
        b = Attackers.ledger_lookup({**t, "story": []})
        assert a == b


def test_scorer_identities():
    T, G = load_task("test_id")[:90], load_gold("test_id")[:90]
    for t, g in zip(T, G):
        gold_pred = {c["id"]: (g["labels"][c["id"]]["label"], g["labels"][c["id"]]["value"].lower()) for c in t["claims"]}
        cs = conflict_set(g, t)
        assert all(score_item(t, g, gold_pred, cs).values())
        keep = {c["id"]: ("KEEP", "") for c in t["claims"]}
        s = score_item(t, g, keep, cs)
        assert s["S0"] == (g["meta"]["category"] == "irrelevant")
        # REVISE-to-prior-value is the same state as KEEP: S2 passes where S0 fails, S1 does not
        same = {c["id"]: ("REVISE", c["value"].lower()) if g["labels"][c["id"]]["label"] == "KEEP" else gold_pred[c["id"]] for c in t["claims"]}
        s2 = score_item(t, g, same, cs)
        assert s2["S2"] and s2["SALL"]
        if any(v["label"] == "KEEP" for v in g["labels"].values()):
            assert not s2["S0"]


def test_identity_rebuild_reproduces_gold_and_ledger():
    d = os.path.join(ADV_DATA, "identity")
    if not os.path.isdir(d):
        pytest.skip("adv data not built")
    G = {g["item_id"]: g for g in load_gold("test_id")}
    T = {t["item_id"]: t for t in load_task("test_id")}
    for g in load_gold("test_id", d):
        assert g["labels"] == G[g["item_id"]]["labels"]
    for t in load_task("test_id", d):
        assert t["claims"] == T[t["item_id"]]["claims"]
