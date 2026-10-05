"""Benchmark-level guarantees: determinism, manifest, exposure, isolation, leakage gates, distinct examples."""
import ast, hashlib, json, os, tempfile
import pytest
from research.ssr_bench import generate as gen, leakage
from research.ssr_bench.io import load_gold, load_task

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEMS_DIR = os.path.join(ROOT, "ssr_bench", "systems")
FORBIDDEN_IMPORTS = {"oracle_a", "oracle_b", "generate", "leakage"}


def test_generation_is_deterministic_and_matches_manifest():
    with tempfile.TemporaryDirectory() as d:
        m = gen.write_all(d)
    on_disk = json.load(open(os.path.join(gen.DATA, "manifest.json")))
    for sp, info in m["splits"].items():
        for k in ("items", "sha256_task", "sha256_gold"):
            assert info[k] == on_disk["splits"][sp][k], f"{sp}.{k}: committed data/ is stale or non-deterministic"
    for sp, info in on_disk["splits"].items():
        for kind in ("task", "gold"):
            h = hashlib.sha256(open(os.path.join(gen.DATA, f"{sp}.{kind}.jsonl"), "rb").read()).hexdigest()
            assert h == info[f"sha256_{kind}"]


def test_task_files_expose_no_gold_or_category():
    assert leakage.g5_exposure() == []


def test_item_ids_do_not_encode_category():
    for sp in ("test_id", "dev"):
        by_pos = {}
        for g in load_gold(sp):
            by_pos.setdefault(g["item_id"].rsplit("-", 1)[1], set()).add(g["meta"]["category"])
        assert all(len(v) > 1 for v in by_pos.values())


def test_every_story_has_all_three_categories_as_matched_pairs():
    for sp in ("test_id", "test_ood_lex"):
        by_story = {}
        for g in load_gold(sp):
            by_story.setdefault(g["story_id"], []).append(g["meta"]["category"])
        assert all(sorted(v) == ["contradictory", "irrelevant", "resolving"] for v in by_story.values())


def test_selective_revision_property_most_claims_are_unchanged():
    # 10 claims per item; resolving items change 1-3, others 0-1: selectivity is the point of the task
    for g in load_gold("test_id"):
        n = sum(v["label"] != "KEEP" for v in g["labels"].values())
        assert n <= 3 and len(g["labels"]) == 10


def test_distinct_examples_not_template_repetition():
    for sp in gen.SPLITS:
        d = leakage.g6_distinct(sp)
        assert d["ratio"] >= 0.95
        assert d["unique_evidence_templates"] >= 30


def test_split_disjointness():
    d = leakage.g7_disjoint()
    assert d["ood_lex_template_overlap_with_train_dev_id"] == []
    assert d["ood_ent_uses_A_pool_entities"] == []
    assert d["ood_struct_signature_overlap"] == [] and d["id_sigs_flagged_ood"] == 0 and d["marker_heldout_in_id"] == []


def test_oracles_agree_on_every_stored_item_recomputed_from_world():
    for sp in gen.SPLITS:
        assert leakage.g8_oracles(sp)["disagreements"] == 0


def test_systems_cannot_import_oracles_or_gold_loaders():
    """Any module under ssr_bench/systems (the only place model code may live) must not touch gold or oracles."""
    if not os.path.isdir(SYSTEMS_DIR):
        pytest.skip("no systems yet")
    for fn in os.listdir(SYSTEMS_DIR):
        if not fn.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(SYSTEMS_DIR, fn)).read())
        for n in ast.walk(tree):
            names = []
            if isinstance(n, ast.ImportFrom):
                names = [(n.module or "").split(".")[-1]] + [a.name for a in n.names]
            elif isinstance(n, ast.Import):
                names = [a.name.split(".")[-1] for a in n.names]
            assert not (set(names) & (FORBIDDEN_IMPORTS | {"load_gold"})), f"{fn} imports {names}"
            assert not (isinstance(n, ast.Constant) and isinstance(n.value, str) and ".gold." in n.value), f"{fn} touches gold file"


@pytest.mark.slow
def test_all_preregistered_leakage_gates_pass():
    with pytest.raises(SystemExit) as e:
        leakage.main()
    assert e.value.code == 0
