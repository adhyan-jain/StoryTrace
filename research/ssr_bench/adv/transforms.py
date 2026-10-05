"""Analysis-only transformation layer (Addendum C). Writes ONLY to research/results/adv/data/<transform>/ ; never to data/.

Gold is always RECOMPUTED by both oracles from the stored world (common.rebuild asserts agreement).
Invariance checks: where a transform must not change the underlying state change (renaming, re-wording, re-ordering),
the recomputed labels are asserted equal to the original labels (modulo renaming / claim permutation).

python -m research.ssr_bench.adv.transforms            # build all, 50-story test_id subsample (the LLM subsample)
"""
from __future__ import annotations
import json, os, random, sys
from typing import Dict, List
from .. import lexicon as lx, oracle_a, oracle_b
from ..generate import category
from ..io import load_gold, load_task
from ..leakage import story_from_world
from ..run import pick_stories
from ..world import Assertion, Event, InvalidIntervention, NOBODY, Story
from . import novel_realize as NR
from .common import ADV_DATA, keys_of, rebuild, write_jsonl

N_STORIES = 50
SPLIT = "test_id"


def rename_world(st: Story, ev, m: Dict[str, str]):
    r = lambda x: m.get(x, x)
    st2 = Story([r(c) for c in st.chars], [r(p) for p in st.props], [r(l) for l in st.locs],
                {r(c): r(l) for c, l in st.init_loc.items()}, {r(p): r(h) for p, h in st.init_holder.items()},
                {r(p): r(l) for p, l in st.init_proploc.items()}, frozenset(r(c) for c in st.init_injured),
                [Event(e.slot, e.kind, r(e.actor), r(e.target), r(e.prop)) for e in st.events], st.n_slots)
    ev2 = (Assertion(ev.slot, ev.attr, r(ev.entity), r(ev.value)) if isinstance(ev, Assertion)
           else Event(ev.slot, ev.kind, r(ev.actor), r(ev.target), r(ev.prop)))
    return st2, ev2


def make_map(st: Story, rng: random.Random, pools: str) -> Dict[str, str]:
    C, P, L = {"A": (lx.CHARS_A, lx.PROPS_A, lx.LOCS_A), "B": (lx.CHARS_B, lx.PROPS_B, lx.LOCS_B)}[pools]
    m = {}
    for olds, pool in ((st.chars, C), (st.props, P), (st.locs, L)):
        for o, n in zip(olds, rng.sample(pool, len(olds))):
            m[o] = n
    return m


def _base_items():
    T, G = load_task(SPLIT), load_gold(SPLIT)
    keep = {t["item_id"] for t in pick_stories(SPLIT, T, N_STORIES)}
    return [(t, g) for t, g in zip(T, G) if t["item_id"] in keep]


def _labels_by_key(task, gold, key_map=lambda k: k):
    return {key_map(k): (gold["labels"][c["id"]]["label"], gold["labels"][c["id"]]["value"]) for c, k in zip(task["claims"], keys_of(task))}


def _check_invariant(t0, g0, t1, g1, key_map=lambda k: k, val_map=lambda v: v):
    a = {k: (l, val_map(v)) for k, (l, v) in _labels_by_key(t0, g0, key_map).items()}
    b = _labels_by_key(t1, g1)
    assert a == b, f"invariance violated on {t0['item_id']}"
    assert g0["meta"]["category"] == g1["meta"]["category"]


def build_simple(name: str, fn):
    rows_t, rows_g = [], []
    for t, g in _base_items():
        t1, g1 = fn(t, g)
        rows_t.append(t1)
        rows_g.append(g1)
    d = os.path.join(ADV_DATA, name)
    write_jsonl(os.path.join(d, f"{SPLIT}.task.jsonl"), rows_t)
    write_jsonl(os.path.join(d, f"{SPLIT}.gold.jsonl"), rows_g)
    return len(rows_t)


def t_identity(t, g):
    t1, g1 = rebuild(t, g, seed="identity")
    return t1, g1


def t_entity(pools):
    def f(t, g):
        st, ev = story_from_world(g["world"])
        rng = random.Random(f"adv/entity/{pools}/{t['item_id']}")
        m = make_map(st, rng, pools)
        st2, ev2 = rename_world(st, ev, m)
        keys2 = [(a, m.get(e, e), s) for a, e, s in keys_of(t)]
        probe = next(k for c, k in zip(t["claims"], keys_of(t)) if c["id"] == t["probe"]["claim_id"])
        t1, g1 = rebuild(t, g, story=st2, ev=ev2, keys=keys2, probe_key=(probe[0], m.get(probe[1], probe[1]), probe[2]), seed=f"entity-{pools}")
        _check_invariant(t, g, t1, g1, key_map=lambda k: (k[0], m.get(k[1], k[1]), k[2]), val_map=lambda v: m.get(v, v))
        return t1, g1
    return f


def t_lex(t, g):
    t1, g1 = rebuild(t, g, held=True, seed="lex")
    _check_invariant(t, g, t1, g1)
    return t1, g1


def t_novel(t, g):
    t1, g1 = rebuild(t, g, realize=NR, seed="novel")
    _check_invariant(t, g, t1, g1)
    return t1, g1


def t_claim_order(t, g):
    t1, g1 = rebuild(t, g, permute_claims=True, seed="claim_order")
    _check_invariant(t, g, t1, g1)
    return t1, g1


def t_story_order(t, g):
    t1, g1 = rebuild(t, g, shuffle=True, seed="story_order")
    _check_invariant(t, g, t1, g1)
    return t1, g1


# ----------------------------------------------------------------------------- matched minimal pairs
def _val(story, attr, ent, slot):
    return oracle_b.value(story, story.events, attr, ent, slot)


def _variants(story: Story, ev):
    """Single-field edits of a resolving event (candidate flips). Yields (tag, new_evidence)."""
    if isinstance(ev, Assertion) or ev.kind == "noop":
        return
    s = ev.slot
    inj = [c for c in story.chars if _val(story, "injured", c, s - 1) == "injured"]
    if ev.kind == "move":
        yield "move_to_current_loc", Event(s, "move", ev.actor, target=_val(story, "loc", ev.actor, s - 1))
        for c in inj:
            yield "move_by_injured", Event(s, "move", c, target=ev.target)
    elif ev.kind in ("injure", "heal"):
        for c in story.chars:
            if c != ev.actor:
                yield f"{ev.kind}_other_actor", Event(s, ev.kind, c)
    elif ev.kind in ("give", "drop", "pickup"):
        for c in story.chars:
            if c != ev.actor:
                yield f"{ev.kind}_other_actor", Event(s, ev.kind, c, target=ev.target, prop=ev.prop)
        for p in story.props:
            if p != ev.prop:
                yield f"{ev.kind}_other_prop", Event(s, ev.kind, ev.actor, target=ev.target, prop=p)


def build_matched_pairs():
    rows_t, rows_g, info = [], [], []
    for t, g in _base_items():
        if g["meta"]["category"] != "resolving":
            continue
        st, ev = story_from_world(g["world"])
        keys = keys_of(t)
        found = {}
        for tag, ev2 in _variants(st, ev):
            try:
                ga = oracle_a.gold(st, ev2, keys)
                gb = oracle_b.gold(st, ev2, keys)
            except (InvalidIntervention, KeyError):
                continue
            if ga != gb:
                continue
            cat = category(ga)
            if cat == "resolving" or cat in found:
                continue
            if cat == "contradictory" and not any(v[0] == "CONFLICT" for v in ga.values()):
                continue                      # conflict claim not in the (unchanged) ledger -> no way to express the label
            found[cat] = (tag, ev2)
        for cat, (tag, ev2) in found.items():
            iid = f"{t['item_id']}-mp-{cat[:3]}"
            t1, g1 = rebuild(t, g, ev=ev2, seed="pair", item_id=iid, meta_update={"pair_of": t["item_id"], "pair_edit": tag})
            rows_t.append(t1)
            rows_g.append(g1)
            info.append({"base": t["item_id"], "variant": iid, "edit": tag, "variant_category": cat})
    d = os.path.join(ADV_DATA, "matched_pairs")
    write_jsonl(os.path.join(d, f"{SPLIT}.task.jsonl"), rows_t)
    write_jsonl(os.path.join(d, f"{SPLIT}.gold.jsonl"), rows_g)
    json.dump(info, open(os.path.join(d, "pairs.json"), "w"), indent=1)
    return info


def main():
    out = {}
    out["identity"] = build_simple("identity", t_identity)
    out["entity_permute_same_pool"] = build_simple("entity_permute_same_pool", t_entity("A"))
    out["entity_permute_cross_pool"] = build_simple("entity_permute_cross_pool", t_entity("B"))
    out["lexical_paraphrase"] = build_simple("lexical_paraphrase", t_lex)
    out["novel_templates"] = build_simple("novel_templates", t_novel)
    out["claim_order_random"] = build_simple("claim_order_random", t_claim_order)
    out["story_order_shuffled"] = build_simple("story_order_shuffled", t_story_order)
    info = build_matched_pairs()
    from collections import Counter
    out["matched_pairs_variants"] = len(info)
    out["matched_pairs_by_category"] = dict(Counter(i["variant_category"] for i in info))
    out["matched_pairs_by_edit"] = dict(Counter(i["edit"] for i in info))
    json.dump(out, open(os.path.join(ADV_DATA, "BUILD_SUMMARY.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
