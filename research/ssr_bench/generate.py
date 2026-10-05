"""Benchmark generator. Writes, per split, a TASK file (what systems may see) and a GOLD file (never shown).

Gold labels are computed only by the oracles; the generator's own forward simulation is used solely to produce
*valid* stories, which both oracles then re-verify. The evidence category (resolving / irrelevant / contradictory)
is DERIVED from oracle output, never assigned by hand.
"""
from __future__ import annotations
import argparse, hashlib, json, os, random
from typing import Dict, List, Optional, Tuple
from . import lexicon as lx, oracle_a, oracle_b
from .realize import claim_statement, evidence_text, question_text, story_sentences
from .world import Assertion, Event, Evidence, InvalidIntervention, Key, NOBODY, Story

VERSION = "ssr-bench-1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
M_CLAIMS = 10

BASE = dict(pools="A", heldout_tpl=False, struct="id", shuffle=False, E=(4, 6), distract=0.5, evslot="late", n_chars=3)
SPLITS: Dict[str, dict] = {
    "train":              dict(BASE, seed=101, stories=200),
    "dev":                dict(BASE, seed=102, stories=60),
    "test_id":            dict(BASE, seed=103, stories=100),
    "test_ood_lex":       dict(BASE, seed=104, stories=100, heldout_tpl=True),
    "test_ood_ent":       dict(BASE, seed=105, stories=100, pools="B"),
    "test_ood_struct":    dict(BASE, seed=106, stories=100, struct="ood"),
    "test_ood_nonlinear": dict(BASE, seed=107, stories=100, shuffle=True),
    "test_ood_length":    dict(BASE, seed=108, stories=100, E=(9, 12), n_chars=4),
    "test_ood_distract":  dict(BASE, seed=109, stories=100, distract=3.0),
    "test_ood_evorder":   dict(BASE, seed=110, stories=100, evslot="early"),
    "test_challenge":     dict(BASE, seed=111, stories=100, pools="NEAR", distract=3.0, shuffle=True, n_chars=4),
}
POOLS = {"A": (lx.CHARS_A, lx.PROPS_A, lx.LOCS_A), "B": (lx.CHARS_B, lx.PROPS_B, lx.LOCS_B),
         "NEAR": (lx.CHARS_NEAR, lx.PROPS_NEAR, lx.LOCS_NEAR)}


def sig_is_ood(sig: Tuple[str, ...]) -> bool:
    return int(hashlib.md5("|".join(sig).encode()).hexdigest(), 16) % 5 == 0


def sample_story(rng: random.Random, cfg: dict) -> Optional[Story]:
    cp, pp, lp = POOLS[cfg["pools"]]
    chars = rng.sample(cp, cfg["n_chars"])
    props = rng.sample(pp, 3 if cfg["n_chars"] > 3 else 2)
    locs = rng.sample(lp, 4 if cfg["n_chars"] == 3 else 5)
    loc = {c: rng.choice(locs) for c in chars}
    holder, ploc = {}, {}
    for p in props:
        holder[p] = rng.choice(chars) if rng.random() < 0.6 else NOBODY
        ploc[p] = loc[holder[p]] if holder[p] != NOBODY else rng.choice(locs)
    inj = {c for c in chars if rng.random() < 0.2}
    n_real = rng.randint(*cfg["E"])
    n_noop = int(round(n_real * cfg["distract"]))
    n_slots = n_real + n_noop + 5
    slots = sorted(rng.sample(range(1, n_slots + 1), n_real + n_noop))
    noop_slots = set(rng.sample(slots, n_noop))
    st = {"loc": dict(loc), "holder": dict(holder), "ploc": dict(ploc), "inj": set(inj)}
    events: List[Event] = []
    sig: List[str] = []
    for s in slots:
        if s in noop_slots:
            events.append(Event(s, "noop", rng.choice(chars)))
            continue
        opts: List[Tuple[float, Event]] = []
        for c in chars:
            for L in locs:
                if L != st["loc"][c] and c not in st["inj"]:
                    opts.append((4.0 / (len(chars) * (len(locs) - 1)), Event(s, "move", c, target=L)))
            for p in props:
                if st["holder"][p] == c:
                    opts.append((1.5 / (len(props) * len(chars)), Event(s, "drop", c, prop=p)))
                    for b in chars:
                        if b != c and st["loc"][b] == st["loc"][c]:
                            opts.append((2.0 / (len(chars) ** 2), Event(s, "give", c, target=b, prop=p)))
                if st["holder"][p] == NOBODY and st["ploc"][p] == st["loc"][c]:
                    opts.append((1.5 / len(chars), Event(s, "pickup", c, prop=p)))
            opts.append((1.0 / len(chars), Event(s, "heal" if c in st["inj"] else "injure", c)))
        if not opts:
            return None
        e = rng.choices([o[1] for o in opts], weights=[o[0] for o in opts])[0]
        events.append(e)
        sig.append(e.kind)
        if e.kind == "move":
            st["loc"][e.actor] = e.target
            for p in props:
                if st["holder"][p] == e.actor:
                    st["ploc"][p] = e.target
        elif e.kind == "give":
            st["holder"][e.prop] = e.target
        elif e.kind == "drop":
            st["holder"][e.prop] = NOBODY
            st["ploc"][e.prop] = st["loc"][e.actor]
        elif e.kind == "pickup":
            st["holder"][e.prop] = e.actor
        elif e.kind == "injure":
            st["inj"].add(e.actor)
        else:
            st["inj"].discard(e.actor)
    if sig_is_ood(tuple(sig)) != (cfg["struct"] == "ood"):
        return None
    story = Story(chars, props, locs, loc, holder, ploc, frozenset(inj), events, n_slots)
    story.signature = tuple(sig)  # type: ignore[attr-defined]
    return story


def domain(story: Story, attr: str) -> List[str]:
    return {"loc": story.locs, "proploc": story.locs, "injured": ["injured", "unharmed"],
            "holder": story.chars + [NOBODY]}[attr]


FAMILY_W = {  # category-independent where achievable; see PREREGISTRATION / design_log
    "resolving": {"move": .30, "give": .16, "pickup": .12, "drop": .12, "injure": .15, "heal": .15},
    "contradictory": {"move": .30, "give": .16, "pickup": .12, "drop": .12, "assertion": .30},
    "irrelevant": {"move": .30, "injure": .12, "heal": .12, "assertion": .30, "noop": .16},
}


def candidate(story: Story, rng: random.Random, cat: str, fam: str, slot: int) -> Optional[Evidence]:
    """State-aware recipe for evidence of family `fam` intended to land in category `cat` (verified later by oracle)."""
    v = lambda a, x: oracle_b.value(story, story.events, a, x, slot - 1)  # generation-time lookup only
    chars, props = story.chars, story.props
    inj = [c for c in chars if v("injured", c) == "injured"]
    well = [c for c in chars if c not in inj]
    if fam == "noop":
        return Event(slot, "noop", rng.choice(chars))
    if fam == "assertion":
        attr = rng.choice(["loc", "holder", "proploc", "injured"])
        ent = rng.choice(chars if attr in ("loc", "injured") else props)
        true = oracle_b.value(story, story.events, attr, ent, slot)
        if cat == "irrelevant":
            return Assertion(slot, attr, ent, true)
        return Assertion(slot, attr, ent, rng.choice([x for x in domain(story, attr) if x != true]))
    if fam == "move":
        if cat == "contradictory":
            return Event(slot, "move", rng.choice(inj), target=rng.choice(story.locs)) if inj else None
        if not well:
            return None
        a = rng.choice(well)
        if cat == "irrelevant":
            return Event(slot, "move", a, target=v("loc", a))
        return Event(slot, "move", a, target=rng.choice([L for L in story.locs if L != v("loc", a)]))
    if fam in ("injure", "heal"):
        pool = (inj if (fam == "injure") == (cat == "irrelevant") else well) if fam == "injure" else (well if cat == "irrelevant" else inj)
        # injure: resolving->well chars, irrelevant->already injured; heal: resolving->injured, irrelevant->well
        return Event(slot, fam, rng.choice(pool)) if pool else None
    holders = {p: v("holder", p) for p in props}
    if fam == "give":
        if cat == "resolving":
            opts = [(h, p, b) for p, h in holders.items() if h != NOBODY for b in chars if b != h and v("loc", b) == v("loc", h)]
            if not opts:
                return None
            h, p, b = rng.choice(opts)
            return Event(slot, "give", h, target=b, prop=p)
        p = rng.choice(props)
        a = rng.choice([c for c in chars if c != holders[p]])
        return Event(slot, "give", a, target=rng.choice([c for c in chars if c != a]), prop=p)
    if fam == "drop":
        if cat == "resolving":
            held = [(h, p) for p, h in holders.items() if h != NOBODY]
            if not held:
                return None
            h, p = rng.choice(held)
            return Event(slot, "drop", h, prop=p)
        p = rng.choice(props)
        return Event(slot, "drop", rng.choice([c for c in chars if c != holders[p]]), prop=p)
    if fam == "pickup":
        if cat == "resolving":
            opts = [(c, p) for p in props if holders[p] == NOBODY for c in chars if v("loc", c) == v("proploc", p)]
            if not opts:
                return None
            c, p = rng.choice(opts)
            return Event(slot, "pickup", c, prop=p)
        held = [p for p in props if holders[p] != NOBODY]
        return Event(slot, "pickup", rng.choice(chars), prop=rng.choice(held)) if held else None
    raise ValueError(fam)


def category(g: Dict[Key, Tuple[str, str]]) -> str:
    labs = {v[0] for v in g.values()}
    return "contradictory" if "CONFLICT" in labs else ("resolving" if "REVISE" in labs else "irrelevant")


class LengthBalancer:
    """Keeps the evidence word-count distribution equal across categories (rejection against the lowest-count category)."""
    CATS = ("resolving", "irrelevant", "contradictory")

    def __init__(self):
        self.n = {c: {} for c in self.CATS}

    @staticmethod
    def bin(text: str) -> int:
        return min(len(text.split()), 11)

    def ok(self, cat: str, text: str, slack: int = 1) -> bool:
        b = self.bin(text)
        return self.n[cat].get(b, 0) <= min(self.n[c].get(b, 0) for c in self.CATS) + slack

    def add(self, cat: str, text: str):
        b = self.bin(text)
        self.n[cat][b] = self.n[cat].get(b, 0) + 1


def sample_evidence(story: Story, rng, cfg, cat: str, bal: LengthBalancer, tries: int = 600):
    free = story.free_slots()
    first, last = min(e.slot for e in story.events), max(e.slot for e in story.events)
    mid = (first + last) / 2
    want_past = rng.random() < 0.5
    pool = [s for s in free if s >= 2 and (s < last) == want_past and (s >= mid if cfg["evslot"] == "late" else s < mid)]
    if not pool:
        pool = [s for s in free if s >= 2 and (s < last) == want_past]
    if not pool:
        return None
    for _ in range(tries):
        fam = rng.choices(list(FAMILY_W[cat]), weights=list(FAMILY_W[cat].values()))[0]
        ev = candidate(story, rng, cat, fam, rng.choice(pool))
        if ev is None:
            continue
        try:
            ga = oracle_a.gold(story, ev, story.all_keys())
        except InvalidIntervention:
            continue
        if category(ga) != cat:
            continue
        text = evidence_text(ev, story, random.Random(rng.random()), cfg["heldout_tpl"])
        if bal.ok(cat, text):
            bal.add(cat, text)
            return ev, ga, text
    return None


def entities_of(ev: Evidence) -> set:
    if isinstance(ev, Assertion):
        return {ev.entity} | ({ev.value} if ev.attr == "holder" else set())
    return {x for x in (ev.actor, ev.prop) if x} | ({ev.target} if ev.kind == "give" else set())


def pick_claims(story, ev, ga, rng, cat):
    keys = story.all_keys()
    changed = [k for k in keys if ga[k][0] == "REVISE"]
    conflict = [k for k in keys if ga[k][0] == "CONFLICT"]
    unchanged = [k for k in keys if ga[k][0] == "KEEP"]
    chosen: List[Key] = []
    if cat == "resolving":
        kk = min(len(changed), rng.choices([1, 2, 3], weights=[5, 3, 2])[0])
        dep = [k for k in changed if k[0] == "proploc"]
        if dep and rng.random() < 0.5:
            chosen.append(rng.choice(dep))
        chosen += rng.sample([k for k in changed if k not in chosen], kk - len(chosen))
    elif cat == "contradictory":
        chosen += conflict
    if cat == "resolving":
        ck = {(k[0], k[1]) for k in chosen}
        restored = [k for k in unchanged if (k[0], k[1]) in ck and k[2] > ev.slot]
        if restored and rng.random() < 0.7:
            chosen.append(rng.choice(restored))
    ents = entities_of(ev) | {k[1] for k in chosen}
    hard = [k for k in unchanged if k[1] in ents and k not in chosen]
    n_hard = min(len(hard), (M_CLAIMS - len(chosen)) // 2)
    late = [k for k in hard if k[2] >= ev.slot]
    early = [k for k in hard if k[2] < ev.slot]
    take = rng.sample(late, min(len(late), (n_hard + 1) // 2))
    take += rng.sample(early, min(len(early), n_hard - len(take)))
    take += rng.sample([k for k in hard if k not in take], n_hard - len(take))
    chosen += take
    rest = [k for k in unchanged if k not in chosen]
    chosen += rng.sample(rest, M_CLAIMS - len(chosen))
    rng.shuffle(chosen)
    return chosen, len(take)


def build_item(story, ev, ga, cfg, rng, split, sid, j, sent_rng, ev_text):
    keys, n_hard = pick_claims(story, ev, ga, rng, category(ga))
    prior = oracle_a.values(story, keys)
    assert prior == oracle_b.values(story, keys), "oracle disagreement on prior values"
    gb = oracle_b.gold(story, ev, keys)
    agree = all(gb[k] == ga[k] for k in keys)
    assert agree, f"oracle disagreement on gold for {ev}"
    ids = {k: f"c{i + 1}" for i, k in enumerate(keys)}
    probe_pool = [k for k in keys if ga[k][0] != "CONFLICT"]
    probe_pool = sorted(probe_pool, key=lambda k: (ga[k][0] != "REVISE", rng.random()))
    pk = probe_pool[0]
    ev_slot = ev.slot
    last = max(e.slot for e in story.events)
    held = cfg["heldout_tpl"]
    task = {
        "item_id": f"{split}-{sid:04d}-{j}",
        "story": story_sentences(story, sent_rng, held, cfg["shuffle"]),
        "evidence": ev_text,
        "claims": [{"id": ids[k], "entity": k[1], "attr": k[0], "slot": k[2], "value": prior[k],
                    "statement": claim_statement(k, prior[k])} for k in keys],
        "probe": {"claim_id": ids[pk], "question": question_text(pk)},
    }
    chg = [k for k in keys if ga[k][0] == "REVISE"]
    gold = {
        "item_id": task["item_id"], "story_id": f"{split}-{sid:04d}", "split": split,
        "labels": {ids[k]: {"label": ga[k][0], "value": ga[k][1]} for k in keys},
        "probe_answer": ga[pk][1] if ga[pk][0] == "REVISE" else prior[pk],
        "meta": {
            "category": category(ga),
            "evidence_kind": "assertion" if isinstance(ev, Assertion) else ("noop" if ev.kind == "noop" else "event:" + ev.kind),
            "evidence_slot": ev_slot, "slot_rel": "past" if ev_slot < last else "future",
            "n_changed": len(chg), "n_claims": len(keys), "n_hard_negatives": n_hard,
            "scope_bounded": any(v[0] == "KEEP" and k[2] > ev_slot and (k[0], k[1]) in
                                 {(c[0], c[1]) for c, w in ga.items() if w[0] == "REVISE"} for k, v in ga.items()),
            "has_dependent_change": any(k[0] == "proploc" for k in chg),
            "signature": list(story.signature), "template_heldout": held, "narration": "shuffled" if cfg["shuffle"] else "linear",
            "n_story_sentences": len(task["story"]), "oracle_agree": agree,
        },
        "world": {"chars": story.chars, "props": story.props, "locs": story.locs, "init_loc": story.init_loc,
                  "init_holder": story.init_holder, "init_proploc": story.init_proploc,
                  "init_injured": sorted(story.init_injured), "n_slots": story.n_slots,
                  "events": [e.__dict__ for e in story.events],
                  "evidence": ev.__dict__ | {"type": type(ev).__name__}},
    }
    return task, gold


def build_split(name: str):
    cfg = SPLITS[name]
    rng = random.Random(f"{VERSION}/{name}/{cfg['seed']}")
    sent_rng = random.Random(f"{VERSION}/{name}/sent/{cfg['seed']}")
    tasks, golds, sid, bal = [], [], 0, LengthBalancer()
    while sid < cfg["stories"]:
        story = sample_story(rng, cfg)
        if story is None:
            continue
        cats = ["resolving", "irrelevant", "contradictory"]
        rng.shuffle(cats)
        built = []
        for j, cat in enumerate(cats):
            got = sample_evidence(story, rng, cfg, cat, bal)
            if got is None:
                built = None
                break
            built.append((j, got))
        if built is None:
            continue
        for j, (ev, ga, txt) in built:
            t, g = build_item(story, ev, ga, cfg, rng, name, sid, j, sent_rng, txt)
            tasks.append(t)
            golds.append(g)
        sid += 1
    return tasks, golds


def write_all(out: str = DATA):
    os.makedirs(out, exist_ok=True)
    manifest = {"version": VERSION, "python_hash_seed_independent": True, "m_claims": M_CLAIMS, "splits": {}}
    for name in SPLITS:
        tasks, golds = build_split(name)
        for suffix, rows in (("task", tasks), ("gold", golds)):
            path = os.path.join(out, f"{name}.{suffix}.jsonl")
            with open(path, "w") as f:
                for r in rows:
                    f.write(json.dumps(r, sort_keys=True) + "\n")
        manifest["splits"][name] = {
            "config": SPLITS[name], "items": len(tasks),
            "sha256_task": hashlib.sha256(open(os.path.join(out, f"{name}.task.jsonl"), "rb").read()).hexdigest(),
            "sha256_gold": hashlib.sha256(open(os.path.join(out, f"{name}.gold.jsonl"), "rb").read()).hexdigest(),
        }
    for fn in ("lexicon.py", "world.py", "oracle_a.py", "oracle_b.py", "realize.py", "generate.py"):
        manifest.setdefault("code_sha256", {})[fn] = hashlib.sha256(open(os.path.join(HERE, fn), "rb").read()).hexdigest()
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DATA)
    m = write_all(ap.parse_args().out)
    print({k: v["items"] for k, v in m["splits"].items()})
