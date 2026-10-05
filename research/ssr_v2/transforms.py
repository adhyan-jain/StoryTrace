"""V2 adversarial transformations (analysis-only; writes research/ssr_v2/data/transforms/<name>/ and results/v2/transform_checks.json).
Subsample: 50 pairs of test_main (D1-D4 = 12/13/12/13 by pair id). For each transform the gold is RECOMPUTED by both oracles from the stored
world; invariance is asserted (category, n_changed, final state modulo renaming); every pair re-passes the hard validators; the text-only replay
oracle (grammar-aware where templates changed) must reach >= 0.98 semantic state-EM."""
from __future__ import annotations
import json, os, random
from collections import defaultdict
from typing import Dict, List
from ..ssr_bench import lexicon as lx, realize
from ..ssr_bench.adv import novel_realize as NR
from ..ssr_bench.leakage import story_from_world
from ..ssr_bench.world import Event, NOBODY, Story
from .build import DATA, domain_of, make_item, render_story, write
from .core import story_valid
from .gen import evidence_text_v1
from .replay import novel_pools, predict_final
from .scorers import aggregate, score_item
from .validators import validate_split

TF = os.path.join(DATA, "transforms")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "research", "results", "v2")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "v2")


def load(name):
    T = [json.loads(l) for l in open(os.path.join(DATA, f"{name}.task.jsonl"))]
    G = [json.loads(l) for l in open(os.path.join(DATA, f"{name}.gold.jsonl"))]
    return T, G


def subsample_pairs(G) -> set:
    by = defaultdict(set)
    for g in G:
        if g["member"] == "A" and g["meta"]["stratum"] in ("D1", "D2", "D3", "D4"):
            by[g["meta"]["stratum"]].add(g["pair_id"])
    keep = set()
    for st, n in (("D1", 12), ("D2", 13), ("D3", 12), ("D4", 13)):
        keep |= set(sorted(by[st])[:n])
    return keep


def rename(st: Story, ev: Event, m: Dict[str, str]):
    r = lambda x: m.get(x, x)
    s2 = Story([r(c) for c in st.chars], [r(p) for p in st.props], [r(l) for l in st.locs], {r(c): r(l) for c, l in st.init_loc.items()},
               {r(p): r(h) for p, h in st.init_holder.items()}, {r(p): r(l) for p, l in st.init_proploc.items()}, frozenset(r(c) for c in st.init_injured),
               [Event(e.slot, e.kind, r(e.actor), r(e.target), r(e.prop)) for e in st.events], st.n_slots)
    return s2, Event(ev.slot, ev.kind, r(ev.actor), r(ev.target), r(ev.prop))


def name_map(st: Story, rng: random.Random, pool: str) -> Dict[str, str]:
    C, P, L = {"A": (lx.CHARS_A, lx.PROPS_A, lx.LOCS_A), "B": (lx.CHARS_B, lx.PROPS_B, lx.LOCS_B)}[pool]
    m = {}
    for olds, pl in ((st.chars, C), (st.props, P), (st.locs, L)):
        for o, n in zip(olds, rng.sample(pl, len(olds))):
            m[o] = n
    return m


def render_heldout(story, seed, shuffle=False):
    return render_story(story, seed, shuffle, heldout=True)


def render_novel(story, seed, shuffle=False):
    intro = render_story(Story(story.chars, story.props, story.locs, story.init_loc, story.init_holder, story.init_proploc, story.init_injured, [], story.n_slots), seed)
    slots = [e.slot for e in story.events]
    byslot = {e.slot: e for e in story.events}
    body = []
    for s in slots:
        e = byslot[s]
        r = random.Random(f"{seed}/{e.slot}")
        body.append(f"{r.choice(NR.MARKERS).format(t=e.slot)} {NR._sentence_for_event(e, r, story)}.")
    return intro + body


def render_intro_reversed(story, seed, shuffle=False):
    lines = render_story(story, seed, shuffle)
    n_intro = len(lines) - len(story.events)
    return list(reversed(lines[:n_intro])) + lines[n_intro:]


def add_noops(story: Story, ev: Event, rng: random.Random, n: int = 4) -> Story:
    free = [s for s in story.free_slots() if s != ev.slot and s >= 1]
    picks = rng.sample(free, min(n, len(free)))
    extra = [Event(s, "noop", rng.choice(story.chars)) for s in picks]
    return Story(story.chars, story.props, story.locs, story.init_loc, story.init_holder, story.init_proploc, story.init_injured,
                 list(story.events) + extra, story.n_slots, story.horizon)


SPECS = ["entity_same_pool", "entity_cross_pool", "narration_shuffle", "evidence_paraphrase", "lexical_story", "novel_templates", "irrelevant_context", "claim_order_intro"]


def build_one(name: str, T, G, keep):
    Tn, Gn, PGn = [], [], {}
    byp = defaultdict(dict)
    for t, g in zip(T, G):
        if t["pair_id"] in keep and t["member"] in ("A", "B"):
            byp[t["pair_id"]][t["member"]] = (t, g)
    checks = {"invariance_failures": 0}
    for pid, mm in sorted(byp.items()):
        prng = random.Random(f"ssr-v2/tf/{name}/{pid}")
        mapping, order, extra_sl = None, None, None
        for member in ("A", "B"):
            t, g = mm[member]
            st, ev = story_from_world(g["world"])
            keys0 = [(c["attr"], c["entity"], c["slot"]) for c in t["claims"]]
            seed = f"ssr-v2/tf/{name}/{pid}"
            kw, heldout_ev, evfn, shuffle = {}, False, None, g["meta"]["narration"] == "shuffled"
            st2, ev2, keys = st, ev, keys0
            if name.startswith("entity"):
                if mapping is None:
                    mapping = name_map(st, random.Random(f"{seed}/map"), "A" if name == "entity_same_pool" else "B")
                st2, ev2 = rename(st, ev, mapping)
                keys = [(a, mapping.get(e, e), s) for a, e, s in keys0]
            elif name == "narration_shuffle":
                shuffle = True
            elif name == "evidence_paraphrase":
                heldout_ev = True
            elif name == "lexical_story":
                kw["render"] = render_heldout
            elif name == "novel_templates":
                kw["render"] = render_novel
                evfn = lambda e, s, sd: NR.evidence_text(e, s, random.Random(sd))
            elif name == "irrelevant_context":
                st2 = add_noops(st, ev, random.Random(f"{seed}/noops"), 4)       # same noops in both members: rng seeded by pair, applied to each story's free slots
                if not story_valid(st2):
                    raise AssertionError("noop insertion invalid")
            elif name == "claim_order_intro":
                order = order or random.Random(f"{seed}/order").sample(range(len(keys0)), len(keys0))
                kw["claim_order"] = order
                kw["render"] = render_intro_reversed
            text = (evfn(ev2, st2, f"{seed}/ev") if evfn else evidence_text_v1(ev2, st2, f"{seed}/ev", heldout_ev))
            t2, g2, prior = make_item(st2, ev2, text, keys, pid, member, f"tf_{name}", seed, shuffle=shuffle,
                                      extra_meta={"stratum": g["meta"]["stratum"], "pivot_slot": g["meta"]["pivot_slot"], "pair_cat": g["meta"]["pair_cat"],
                                                  "origin": g["meta"]["origin"], "base_item": g["item_id"]}, **kw)
            # invariance: category and n_changed unchanged; final state equal modulo renaming (values mapped), matched by claim KEY
            m = mapping or {}
            def keyed(task, gold, mp=lambda x: x):
                return {(c["attr"], mp(c["entity"]), c["slot"]): mp(gold["final"][c["id"]]) for c in task["claims"]}
            a = keyed(t, g, lambda x: m.get(x, x)) if name.startswith("entity") else keyed(t, g)
            b = keyed(t2, g2)
            if a != b or g["meta"]["category"] != g2["meta"]["category"] or g["meta"]["n_changed"] != g2["meta"]["n_changed"]:
                checks["invariance_failures"] += 1
            Tn.append(t2), Gn.append(g2)
            PGn[t2["item_id"]] = prior
    write(os.path.join(TF, name), "test_main_sub50", Tn, Gn, PGn)
    pools = novel_pools() if name == "novel_templates" else None
    rows = [score_item(t, g, predict_final(t, privileged=name in ("evidence_paraphrase", "lexical_story"), pools=pools)) for t, g in zip(Tn, Gn)]
    checks["replay_semantic"] = aggregate(rows)["state_em_semantic"]
    v = validate_split(Tn, Gn)
    checks["pairs"], checks["pairs_with_violations"] = v["pairs"], v["pairs_with_violations"]
    checks["violation_examples"] = dict(list(v["violations"].items())[:3])
    return checks


def main():
    T, G = load("test_main")
    keep = subsample_pairs(G)
    out = {"subsample_pairs": len(keep)}
    for name in SPECS:
        out[name] = build_one(name, T, G, keep)
        print(name, {k: v for k, v in out[name].items() if k != "violation_examples"}, flush=True)
    json.dump(out, open(os.path.join(RES, "transform_checks.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
