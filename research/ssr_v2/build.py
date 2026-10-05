"""V2 dataset builder: train / dev / test_main (+ length control) / set-valued. Writes research/ssr_v2/data/. V1 is imported read-only.

Task files expose only whitelisted keys (no gold, no prior values). Gold files hold prior/final/labels/valid sets/meta/world.
PG prior values (used only by condition PG) are in <split>.pgprior.json, never in the task file.
"""
from __future__ import annotations
import hashlib, json, os, random, sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
from ..ssr_bench import lexicon as lx, realize
from ..ssr_bench.generate import BASE, sample_story
from ..ssr_bench.world import Event, InvalidIntervention, Key, NOBODY, Story
from .core import ancestor_closure, claim_keys, core_keys, final_state, story_valid, support_set
from .gen import category, evidence_text_v1, find_pairs, random_event, revision

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CFG_BASE = dict(BASE, E=(6, 9), n_chars=4, distract=0.5)
CFG_LONG = dict(BASE, E=(6, 9), n_chars=4, distract=3.0)
CFG_MIX = [dict(BASE, E=(4, 6)), dict(BASE, E=(7, 9)), CFG_BASE, CFG_LONG]
TASK_KEYS = {"item_id", "pair_id", "member", "story", "evidence", "claims", "chars", "props", "locs"}


# ----------------------------------------------------------------------------- rendering (per-event seeds keep unchanged sentences identical across a pair)
def render_story(story: Story, seed: str, shuffle: bool = False, heldout: bool = False) -> List[str]:
    intro = []
    for c in story.chars:
        intro.append(f"{lx.INTRO_MARK} " + lx.INTRO_TPL["loc"].format(a=c, L=story.init_loc[c]))
    for p in story.props:
        h = story.init_holder[p]
        intro.append(f"{lx.INTRO_MARK} " + (lx.INTRO_TPL["holder"].format(a=h, p=p) if h != NOBODY else lx.INTRO_TPL["ground"].format(p=p, L=story.init_proploc[p])))
    for c in sorted(story.init_injured):
        intro.append(f"{lx.INTRO_MARK} " + lx.INTRO_TPL["injured"].format(a=c))
    slots = [e.slot for e in story.events]
    if shuffle:
        random.Random(f"{seed}/shuffle").shuffle(slots)
    byslot = {e.slot: e for e in story.events}
    body = []
    for s in slots:
        e = byslot[s]
        r = random.Random(f"{seed}/{e.slot}")
        body.append(f"{realize.marker(e.slot, r, heldout)} {realize._sentence_for_event(e, r, heldout, story)}.")
    return intro + body


def domain_of(story: Story, attr: str) -> List[str]:
    return {"loc": story.locs, "proploc": story.locs, "injured": ["injured", "unharmed"], "holder": story.chars + [NOBODY]}[attr]


def world_dict(story: Story, ev) -> dict:
    return {"chars": story.chars, "props": story.props, "locs": story.locs, "init_loc": story.init_loc, "init_holder": story.init_holder,
            "init_proploc": story.init_proploc, "init_injured": sorted(story.init_injured), "n_slots": story.n_slots,
            "events": [e.__dict__ for e in story.events], "evidence": ev.__dict__ | {"type": "Event"}}


def make_item(story: Story, ev: Event, text: str, keys: List[Key], pair_id: str, member: str, split: str, seed: str,
              shuffle: bool = False, valid_alts: Optional[List[Event]] = None, extra_meta: Optional[dict] = None, render=None, claim_order=None):
    prior, final, labels = final_state(story, ev, keys)
    if claim_order is not None:
        keys = [keys[i] for i in claim_order]
    ids = {k: f"c{i + 1}" for i, k in enumerate(keys)}
    valid = [{ids[k]: final[k] for k in keys}]
    if valid_alts:
        valid = []
        for alt in valid_alts:
            _, f, _ = final_state(story, alt, keys)
            valid.append({ids[k]: f[k] for k in keys})
    sup = support_set(story, ev, keys)
    iid = f"{split}-{pair_id}-{member}"
    task = {"item_id": iid, "pair_id": pair_id, "member": member,
            "story": (render or render_story)(story, seed, shuffle), "evidence": text,
            "claims": [{"id": ids[k], "entity": k[1], "attr": k[0], "slot": k[2], "question": realize.question_text(k), "domain": domain_of(story, k[0])} for k in keys],
            "chars": story.chars, "props": story.props, "locs": story.locs}
    meta = {"category": category(labels), "depth": len(sup), "anc_depth": len(ancestor_closure(story, ev, keys)),
            "n_events": len(story.events), "n_sentences": len(task["story"]), "n_changed": sum(final[k] != prior[k] for k in keys),
            "evidence_slot": ev.slot, "evidence_kind": ev.kind, "narration": "shuffled" if shuffle else "linear", "set_valued": bool(valid_alts)}
    meta.update(extra_meta or {})
    gold = {"item_id": iid, "pair_id": pair_id, "member": member, "split": split, "prior": {ids[k]: prior[k] for k in keys},
            "final": {ids[k]: final[k] for k in keys}, "labels": {ids[k]: labels[k] for k in keys}, "valid_final": valid, "meta": meta,
            "world": world_dict(story, ev)}
    return task, gold, {ids[k]: prior[k] for k in keys}


# ----------------------------------------------------------------------------- pair collection
def collect(cfg: dict, seed: str, want: Dict[int, int], max_samples: int, depth_key: str = "depth"):
    """-> {depth: [pair dicts]} with one pair per story, equal depth in both members, up to `want[depth]` each."""
    rng = random.Random(seed)
    pools: Dict[int, List[dict]] = defaultdict(list)
    n = 0
    while n < max_samples and any(len(pools[d]) < want[d] for d in want):
        n += 1
        got = None
        story = sample_story(rng, cfg)
        if story is None:
            continue
        ev = random_event(story, rng)
        if ev is None:
            continue
        text = evidence_text_v1(ev, story, f"{rng.random()}")
        open_d = {d for d in want if len(pools[d]) < want[d]}
        try:   # cheap pre-filter: run the (expensive) pair search only if this evidence's causal depth is still needed
            ks = claim_keys(story, ev, text)
            final_state(story, ev, ks)
            if len(support_set(story, ev, ks)) not in open_d:
                continue
        except (InvalidIntervention, KeyError):
            continue
        ps = [p for p in find_pairs(story, ev, text) if p["depth1"] == p["depth2"] and p["depth2"] in open_d]
        if not ps:
            continue
        # one pair per story: prefer the pair whose pivot is closest to the evidence (most local contrast), then smallest anc depth
        p = sorted(ps, key=lambda q: (abs(q["pivot"] - q["ev"].slot), q["anc2"]))[0]
        pools[p["depth2"]].append(p)
    return pools, n


def build_split(name: str, pairs: List[dict], out_dir: str, seed_prefix: str, shuffle: bool = False, extra: Optional[dict] = None):
    T, G, PG = [], [], {}
    rng = random.Random(f"{seed_prefix}/assign")
    pairs = list(pairs)
    rng.shuffle(pairs)                      # pair ids carry no information about depth/stratum
    for i, p in enumerate(pairs):
        pid = f"{i:04d}"
        seed = f"{seed_prefix}/{pid}"
        order = [("sampled", p["S2"]), ("variant", p["S1"])]
        if rng.random() < 0.5:              # which story is member A vs B is a fair coin (no systematic origin pattern)
            order.reverse()
        for member, (origin, story) in zip(("A", "B"), order):
            em = {"stratum": p.get("stratum", ""), "pivot_slot": p["pivot"], "pair_cat": f"{p['cat1']}|{p['cat2']}", "origin": origin}
            em.update(extra or {})
            t, g, prior = make_item(story, p["ev"], p["text"], p["keys"], pid, member, name, seed, shuffle=shuffle, extra_meta=em)
            T.append(t)
            G.append(g)
            PG[t["item_id"]] = prior
    write(out_dir, name, T, G, PG)
    return T, G


def write(out_dir: str, name: str, T, G, PG):
    os.makedirs(out_dir, exist_ok=True)
    for suffix, rows in (("task", T), ("gold", G)):
        with open(os.path.join(out_dir, f"{name}.{suffix}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True) + "\n")
    json.dump(PG, open(os.path.join(out_dir, f"{name}.pgprior.json"), "w"), sort_keys=True)


def match_histogram(pools: Dict[int, List[dict]], depths, per: int, rng: random.Random):
    """Pick `per` pairs per depth with the SAME n_events histogram (target = the scarcest depth's selection)."""
    scarce = min(depths, key=lambda d: len(pools[d]))
    tgt = Counter(p["n_events"] for p in rng.sample(pools[scarce], min(per, len(pools[scarce]))))
    out = {}
    for d in depths:
        pool = list(pools[d])
        rng.shuffle(pool)
        chosen, need = [], dict(tgt)
        for p in pool:
            if need.get(p["n_events"], 0) > 0:
                chosen.append(p)
                need[p["n_events"]] -= 1
        out[d] = chosen
    return out, tgt


# ----------------------------------------------------------------------------- set-valued (disjunctive evidence)
def disjunctive_items(n: int, seed: str, split: str):
    rng = random.Random(seed)
    T, G, PG = [], [], {}
    tries = 0
    while len(T) < n and tries < 40000:
        tries += 1
        story = sample_story(rng, CFG_BASE)
        if story is None:
            continue
        free = [s for s in story.free_slots() if s >= 2]
        if not free:
            continue
        d, a = rng.choice(free), rng.choice(story.chars)
        L1, L2 = rng.sample(story.locs, 2)
        e1, e2 = Event(d, "move", a, target=L1), Event(d, "move", a, target=L2)
        text = f"{realize.marker(d, random.Random(f'{seed}/{tries}'), False)} {a} went to either the {L1} or the {L2}, though it was unclear which."
        keys = claim_keys(story, e1, text)
        try:
            _, f1, l1 = final_state(story, e1, keys)
            _, f2, l2 = final_state(story, e2, keys)
        except (InvalidIntervention, KeyError):
            continue
        if category(l1) != "resolving" or category(l2) != "resolving" or f1 == f2:
            continue
        pid = f"{len(T):04d}"
        t, g, prior = make_item(story, e1, text, keys, pid, "SV", split, f"{seed}/{pid}", valid_alts=[e1, e2], extra_meta={"stratum": "set_valued"})
        T.append(t)
        G.append(g)
        PG[t["item_id"]] = prior
    return T, G, PG


# ----------------------------------------------------------------------------- orchestration
def sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(out_dir: str = DATA):
    manifest = {"version": "ssr-v2-1.0", "prereg": "research/ssr_bench/V2_PREREGISTRATION.md", "splits": {}}
    rng = random.Random("ssr-v2/select")
    # train: mixed configs, all depths
    tp, n_tr = [], 0
    for i, cfg in enumerate(CFG_MIX):
        want = {0: 30, 1: 50, 2: 50, 3: 15} if i < 2 else {0: 30, 1: 50, 2: 50, 3: 25, 4: 10}
        pools, n = collect(cfg, f"ssr-v2/train/{i}", want, 25000)
        for d, ps in pools.items():
            tp += ps
        n_tr += n
    for p in tp:
        p["stratum"] = f"D{p['depth2']}"
    build_split("train", tp, out_dir, "ssr-v2/train")
    # dev: 20 pairs, depths 1-3
    pools, _ = collect(CFG_BASE, "ssr-v2/dev", {1: 7, 2: 7, 3: 6}, 20000)
    dp = [dict(p, stratum=f"D{d}") for d, ps in pools.items() for p in ps]
    build_split("dev", dp, out_dir, "ssr-v2/dev")
    # test_main: D1..D4 matched on n_events, + length control (D2 from the long config)
    pools, n_main = collect(CFG_BASE, "ssr-v2/test_main", {1: 100, 2: 100, 3: 80, 4: 45}, 150000)
    sel, tgt = match_histogram(pools, [1, 2, 3, 4], 30, rng)
    test_pairs = []
    for d in (1, 2, 3, 4):
        for p in sel[d]:
            test_pairs.append(dict(p, stratum=f"D{d}"))
    lpools, _ = collect(CFG_LONG, "ssr-v2/test_long", {2: 80}, 80000)
    long_pairs = [dict(p, stratum="D2_long") for p in sorted(lpools[2], key=lambda q: -q["n_events"])[:30]]
    build_split("test_main", test_pairs + long_pairs, out_dir, "ssr-v2/test_main")
    # set-valued
    T, G, PG = disjunctive_items(30, "ssr-v2/setvalued", "set_valued")
    write(out_dir, "set_valued", T, G, PG)
    for name in ("train", "dev", "test_main", "set_valued"):
        manifest["splits"][name] = {"sha256_task": sha(os.path.join(out_dir, f"{name}.task.jsonl")), "sha256_gold": sha(os.path.join(out_dir, f"{name}.gold.jsonl"))}
    manifest["selection"] = {"test_main_n_events_histogram": dict(tgt), "per_depth_selected": {d: len(sel[d]) for d in sel},
                             "long_pairs": len(long_pairs), "set_valued_items": len(T), "train_pairs": len(tp), "dev_pairs": len(dp)}
    json.dump(manifest, open(os.path.join(out_dir, "manifest.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(manifest["selection"], indent=1))


if __name__ == "__main__":
    main()
