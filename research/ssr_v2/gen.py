"""V2 matched-pair generator. Imports V1 only read-only (world types, story sampler, oracles).

A PAIR = (S1, S2, evidence, claim keys): S1 differs from S2 in exactly ONE event sentence; evidence text and claim keys are
byte-identical; both stories are valid under both oracles; the revisions (non-KEEP claims with their values) DIFFER, so no
story-blind function can be right on both members. Depth = |support set| (see core.support_set).
"""
from __future__ import annotations
import random
from collections import Counter
from typing import Dict, Iterator, List, Optional, Tuple
from ..ssr_bench.generate import BASE, sample_story
from ..ssr_bench.world import Event, InvalidIntervention, NOBODY, Story
from .core import ancestor_closure, claim_keys, final_state, story_valid, support_set

KIND_W = {"move": 0.30, "give": 0.16, "pickup": 0.12, "drop": 0.12, "injure": 0.15, "heal": 0.15}


def random_event(story: Story, rng: random.Random) -> Optional[Event]:
    free = [s for s in story.free_slots() if s >= 2]
    if not free:
        return None
    d = rng.choice(free)
    k = rng.choices(list(KIND_W), weights=list(KIND_W.values()))[0]
    a = rng.choice(story.chars)
    if k == "move":
        return Event(d, "move", a, target=rng.choice(story.locs))
    if k == "give":
        return Event(d, "give", a, target=rng.choice([c for c in story.chars if c != a]), prop=rng.choice(story.props))
    if k in ("pickup", "drop"):
        return Event(d, k, a, prop=rng.choice(story.props))
    return Event(d, k, a)


def evidence_text_v1(ev: Event, story: Story, seed: str, heldout: bool = False) -> str:
    from ..ssr_bench import realize
    return realize.evidence_text(ev, story, random.Random(seed), heldout)


def variants(e: Event, story: Story) -> Iterator[Event]:
    s = e.slot
    if e.kind != "noop":
        yield Event(s, "noop", e.actor)
    else:
        for c in story.chars:
            yield Event(s, "injure", c)
            yield Event(s, "heal", c)
        for c in story.chars:
            for L in story.locs:
                yield Event(s, "move", c, target=L)
    if e.kind == "move":
        for L in story.locs:
            if L != e.target:
                yield Event(s, "move", e.actor, target=L)
        for c in story.chars:
            if c != e.actor:
                yield Event(s, "move", c, target=e.target)
    elif e.kind == "give":
        for c in story.chars:
            if c not in (e.target, e.actor):
                yield Event(s, "give", e.actor, target=c, prop=e.prop)
            if c not in (e.actor, e.target):
                yield Event(s, "give", c, target=e.target, prop=e.prop)
        for p in story.props:
            if p != e.prop:
                yield Event(s, "give", e.actor, target=e.target, prop=p)
    elif e.kind in ("pickup", "drop"):
        for c in story.chars:
            if c != e.actor:
                yield Event(s, e.kind, c, prop=e.prop)
        for p in story.props:
            if p != e.prop:
                yield Event(s, e.kind, e.actor, prop=p)
    elif e.kind in ("injure", "heal"):
        yield Event(s, "heal" if e.kind == "injure" else "injure", e.actor)
        for c in story.chars:
            if c != e.actor:
                yield Event(s, e.kind, c)


def replace_event(story: Story, old: Event, new: Event) -> Story:
    return Story(story.chars, story.props, story.locs, story.init_loc, story.init_holder, story.init_proploc, story.init_injured,
                 [new if e.slot == old.slot else e for e in story.events], story.n_slots, story.horizon)


def revision(prior, final, labels) -> Dict:
    return {k: (labels[k], final[k]) for k in final if labels[k] != "KEEP"}


def category(labels: Dict) -> str:
    v = set(labels.values())
    return "blocked" if "CONFLICT" in v else ("resolving" if "REVISE" in v else "irrelevant")


def find_pairs(S2: Story, ev: Event, text: str, max_pairs: int = 20) -> List[dict]:
    keys = claim_keys(S2, ev, text)
    try:
        p2, f2, l2 = final_state(S2, ev, keys)
    except (InvalidIntervention, KeyError):
        return []
    r2 = revision(p2, f2, l2)
    sup2 = support_set(S2, ev, keys)
    out = []
    for e in list(S2.events):
        for v in variants(e, S2):
            S1 = replace_event(S2, e, v)
            if not story_valid(S1):
                continue
            try:
                p1, f1, l1 = final_state(S1, ev, keys)
            except (InvalidIntervention, KeyError):
                continue
            r1 = revision(p1, f1, l1)
            if r1 == r2:
                continue
            # Amendment 1: some claim at slot >= evidence day must have a DIFFERENT gold final value between the members,
            # so a story-blind function (same output for both) is wrong on that claim in at least one member.
            if not any(f1[k] != f2[k] for k in keys if k[2] >= ev.slot):
                continue
            sup1 = support_set(S1, ev, keys)
            out.append(dict(S1=S1, S2=S2, ev=ev, text=text, keys=keys, pivot=e.slot, pivot_old=e, pivot_new=v,
                            cat1=category(l1), cat2=category(l2), depth1=len(sup1), depth2=len(sup2),
                            anc1=len(ancestor_closure(S1, ev, keys)), anc2=len(ancestor_closure(S2, ev, keys)),
                            n_events=len(S2.events), n_sentences=len(S2.events) + len(S2.chars) + len(S2.props)))
            if len(out) >= max_pairs:
                return out
    return out


def sample_item(rng: random.Random, cfg: dict):
    story = sample_story(rng, cfg)
    if story is None:
        return None
    ev = random_event(story, rng)
    if ev is None:
        return None
    text = evidence_text_v1(ev, story, f"{rng.random()}")
    return story, ev, text


def pilot(n: int, seed: int = 7, cfgs=None) -> dict:
    """Feasibility counts only (no attackers, no LLMs). Reports achievable pair counts by depth and category transition."""
    rng = random.Random(seed)
    cfgs = cfgs or [dict(BASE, E=(4, 6)), dict(BASE, E=(7, 9)), dict(BASE, E=(7, 9), n_chars=4)]
    tried = valid = with_pair = 0
    by_depth, by_trans, by_cfg_depth = Counter(), Counter(), Counter()
    eq_depth = 0
    n_pairs = 0
    for i in range(n):
        cfg = cfgs[i % len(cfgs)]
        got = sample_item(rng, cfg)
        tried += 1
        if got is None:
            continue
        S2, ev, text = got
        ps = find_pairs(S2, ev, text)
        if not ps:
            continue
        with_pair += 1
        for p in ps:
            n_pairs += 1
            by_depth[(p["depth2"], p["depth1"])] += 1
            by_trans[(p["cat1"], p["cat2"])] += 1
            by_cfg_depth[(i % len(cfgs), p["depth2"])] += 1
            eq_depth += p["depth1"] == p["depth2"]
    return {"samples": tried, "samples_with_>=1_pair": with_pair, "pairs_total": n_pairs, "pairs_equal_depth": eq_depth,
            "depth(S2,S1)": {str(k): v for k, v in sorted(by_depth.items())}, "category(S1,S2)": {str(k): v for k, v in by_trans.items()},
            "cfg_depth": {str(k): v for k, v in sorted(by_cfg_depth.items())}}


if __name__ == "__main__":
    import json, sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    out = pilot(n)
    json.dump(out, open("research/results/v2/feasibility_pilot.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
