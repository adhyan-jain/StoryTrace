"""V2 integrity tests: V1 untouched, no gold in task files, pair validators, replay oracle ceiling, scorer identities, attacker isolation, prompt overlap."""
import ast, hashlib, json, os
import pytest
from research.ssr_v2 import prompts as P
from research.ssr_v2.build import DATA, TASK_KEYS
from research.ssr_v2.replay import predict_final
from research.ssr_v2.scorers import aggregate, score_item
from research.ssr_v2.validators import validate_split

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SSR = os.path.join(ROOT, "research", "ssr_bench")
SNAP = os.path.join(ROOT, "research", "results", "snapshot_2026-10-02", "BENCHMARK_HASHES.txt")
V2 = os.path.join(ROOT, "research", "ssr_v2")


def load(name):
    p = os.path.join(DATA, f"{name}.task.jsonl")
    if not os.path.exists(p):
        pytest.skip("V2 data not built")
    return ([json.loads(l) for l in open(p)], [json.loads(l) for l in open(os.path.join(DATA, f"{name}.gold.jsonl"))])


def test_v1_files_unchanged():
    for line in open(SNAP):
        d, path = line.split()
        assert hashlib.sha256(open(os.path.join(SSR, path), "rb").read()).hexdigest() == d, path


def test_task_files_expose_only_whitelisted_keys_and_no_gold():
    for name in ("train", "dev", "test_main", "set_valued"):
        T, _ = load(name)
        for t in T:
            assert set(t) == TASK_KEYS
            assert all(set(c) == {"id", "entity", "attr", "slot", "question", "domain"} for c in t["claims"])
            assert t["member"] in ("A", "B", "SV")


def test_pair_ids_and_members_carry_no_origin_or_stratum_information():
    T, G = load("test_main")
    origins = [g["meta"]["origin"] for g in G if g["member"] == "A"]
    assert 0.3 < origins.count("sampled") / len(origins) < 0.7           # A is a fair coin between sampled and variant
    from scipy.stats import spearmanr
    ids = [int(g["pair_id"]) for g in G if g["member"] == "A"]
    depth = [g["meta"]["depth"] for g in G if g["member"] == "A"]
    assert spearmanr(ids, depth).pvalue > 0.01          # pair id carries no depth information


def test_all_pairs_satisfy_hard_validators():
    for name in ("train", "dev", "test_main"):
        T, G = load(name)
        r = validate_split(T, G)
        assert r["pairs_with_violations"] == 0, r["violations"]


def test_replay_oracle_reaches_ceiling():
    for name in ("dev", "test_main", "set_valued"):
        T, G = load(name)
        rows = [score_item(t, g, predict_final(t)) for t, g in zip(T, G)]
        assert aggregate(rows)["state_em_semantic"] >= 0.98, name


def test_scorer_identities():
    T, G = load("dev")
    for t, g in zip(T, G):
        s = score_item(t, g, g["final"])
        assert s["strict"] and s["semantic"] and s["collateral"] == 0 and s["under"] == 0 and not s["inconsistent"]
        prior = score_item(t, g, g["prior"])        # answering with the PRIOR state = never revising
        assert prior["over"] == 0
        if g["meta"]["n_changed"] > 0:
            assert not prior["semantic"] and prior["under"] == g["meta"]["n_changed"]
        bad = {c["id"]: "zzz" for c in t["claims"]}
        assert score_item(t, g, bad)["invalid"] == len(t["claims"])


def test_set_valued_accepts_every_valid_world_and_rejects_mixtures():
    T, G = load("set_valued")
    for t, g in zip(T, G):
        assert len(g["valid_final"]) == 2
        for w in g["valid_final"]:
            assert score_item(t, g, w)["semantic"]
        a, b = g["valid_final"]
        diff = [i for i in a if a[i] != b[i]]
        if len(diff) >= 2:
            mix = dict(a)
            mix[diff[0]] = b[diff[0]]
            assert not score_item(t, g, mix)["semantic"]


def test_attackers_and_replay_do_not_import_oracles_or_generator():
    for fn in ("attackers.py", "replay.py", "scorers.py"):
        tree = ast.parse(open(os.path.join(V2, fn)).read())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                mods.add((n.module or "").split(".")[-1])
                mods.update(a.name for a in n.names)
        assert not ({"oracle_a", "oracle_b", "generate", "core", "gen", "build"} & mods), fn


def test_paraphrased_rule_prompts_overlap_original_below_threshold():
    base = P.LAWS_IMPERATIVE + " " + P.K1_TASK
    assert P.ngram_jaccard(base, P.K3A) < 0.25 and P.ngram_jaccard(base, P.K3B) < 0.25


def test_pg_prior_is_not_in_task_files():
    T, _ = load("dev")
    assert not any("prior" in json.dumps(t) and '"prior"' in json.dumps(t) for t in T)


def test_external_set_real_execution_ceiling_and_validators():
    from research.ssr_v2.external import replay_exec
    T, G = load("external")
    assert validate_split(T, G)["pairs_with_violations"] == 0
    rows = [score_item(t, g, replay_exec(t)) for t, g in zip(T, G)]
    assert all(r["semantic"] for r in rows)
    assert all(set(t) == TASK_KEYS for t in T)


def test_transformed_sets_pass_validators_and_invariance():
    chk = os.path.join(ROOT, "research", "results", "v2", "transform_checks.json")
    if not os.path.exists(chk):
        pytest.skip("transforms not built")
    d = json.load(open(chk))
    for k, v in d.items():
        if isinstance(v, dict):
            assert v["invariance_failures"] == 0 and v["pairs_with_violations"] == 0 and v["replay_semantic"] >= 0.98, k


def test_external_prompt_uses_command_log_wording_and_no_synthetic_laws():
    from research.ssr_v2 import prompts as PP
    T, G = load("external")
    t = T[0]
    pg = json.load(open(os.path.join(DATA, "external.pgprior.json")))
    s = PP.build_prompt("PG", t, prior=pg[t["item_id"]])
    assert "COMMAND LOG" in s and "story before the new sentence" not in s and "injured" not in s
