"""SSR V2 core (new namespace; V1 files are imported read-only).

- tracer: own replay that records, for every state variable, the LAST WRITER event; used to define the causal support set of an
  evidence sentence (the prior events whose values must be known to decide the revision). It is independent of the oracles.
- claim_keys(): label-independent claim-set rule (a function of the evidence surface form and story SHAPE only).
- final_state(): gold final value per claim from the V1 oracles (prior value unless the oracle says REVISE).
Variables: ("loc", c) ("holder", p) ("ploc", p) ("inj", c). Claim attr -> variable: loc->loc, holder->holder, proploc->ploc, injured->inj.
"""
from __future__ import annotations
import hashlib, random
from typing import Dict, List, Optional, Sequence, Set, Tuple
from ..ssr_bench import oracle_a, oracle_b
from ..ssr_bench.world import Assertion, Event, InvalidIntervention, Key, NOBODY, Story

ATTR_VAR = {"loc": "loc", "holder": "holder", "proploc": "ploc", "injured": "inj"}
M_CLAIMS = 10


def _init(story: Story) -> dict:
    return {"loc": dict(story.init_loc), "holder": dict(story.init_holder), "ploc": {p: story.init_proploc.get(p, "") for p in story.props},
            "inj": set(story.init_injured)}


def reads_of(ev: Event, story: Story) -> List[Tuple[str, str]]:
    k, a, p = ev.kind, ev.actor, ev.prop
    if k == "move":
        return [("inj", a)] + [("holder", q) for q in story.props]
    if k == "give":
        return [("holder", p), ("loc", a), ("loc", ev.target)]
    if k == "pickup":
        return [("holder", p), ("ploc", p), ("loc", a)]
    if k == "drop":
        return [("holder", p), ("loc", a)]
    if k in ("injure", "heal"):
        return [("inj", a)]
    return []


def writes_of(ev: Event, st: dict) -> List[Tuple[str, str]]:
    k, a, p = ev.kind, ev.actor, ev.prop
    if k == "move":
        return [("loc", a)] + [("ploc", q) for q, h in st["holder"].items() if h == a]
    if k == "give":
        return [("holder", p)]
    if k == "pickup":
        return [("holder", p)]
    if k == "drop":
        return [("holder", p), ("ploc", p)]
    if k in ("injure", "heal"):
        return [("inj", a)]
    return []


def apply(st: dict, e: Event) -> bool:
    """Same semantics as oracle_a._apply (own implementation). Returns True if the event is possible."""
    if e.kind == "move":
        if e.actor in st["inj"]:
            return False
        st["loc"][e.actor] = e.target
        for q, h in st["holder"].items():
            if h == e.actor:
                st["ploc"][q] = e.target
    elif e.kind == "give":
        if st["holder"][e.prop] != e.actor:
            return False
        st["holder"][e.prop] = e.target
    elif e.kind == "pickup":
        if st["holder"][e.prop] != NOBODY:
            return False
        st["holder"][e.prop] = e.actor
    elif e.kind == "drop":
        if st["holder"][e.prop] != e.actor:
            return False
        st["holder"][e.prop] = NOBODY
        st["ploc"][e.prop] = st["loc"][e.actor]
    elif e.kind == "injure":
        st["inj"].add(e.actor)
    elif e.kind == "heal":
        st["inj"].discard(e.actor)
    return True


def tracer(story: Story, extra: Optional[Event] = None):
    """-> (writers_at, state_at): for each slot 0..horizon the last-writer slot per variable (0 = initial state) and the state."""
    st = _init(story)
    writer: Dict[Tuple[str, str], int] = {}
    evs = {e.slot: e for e in story.events}
    if extra is not None:
        evs[extra.slot] = extra
    W, S = [dict(writer)], [{"loc": dict(st["loc"]), "holder": dict(st["holder"]), "ploc": dict(st["ploc"]), "inj": set(st["inj"])}]
    for s in range(1, story.horizon + 1):
        if s in evs:
            e = evs[s]
            ws = writes_of(e, st)
            if apply(st, e):
                for v in ws:
                    writer[v] = s
        W.append(dict(writer))
        S.append({"loc": dict(st["loc"]), "holder": dict(st["holder"]), "ploc": dict(st["ploc"]), "inj": set(st["inj"])})
    return W, S


def claim_var(k: Key) -> Tuple[str, str]:
    return (ATTR_VAR[k[0]], k[1])


def support_set(story: Story, ev: Event, keys: Sequence[Key]) -> Set[int]:
    """Slots of the prior/following events whose values are needed to decide the revision of `ev`:
    last writers (before ev) of every variable `ev` reads + first later overwriter of every variable `ev` writes that some claim reads after it."""
    d = ev.slot
    W, S = tracer(story)
    sup = {W[d - 1].get(v, 0) for v in reads_of(ev, story)} - {0}
    st = S[d - 1]
    wv = set(writes_of(ev, st))
    later = sorted(e.slot for e in story.events if e.slot > d)
    for v in wv:
        for s in later:
            e = next(x for x in story.events if x.slot == s)
            if v in set(writes_of(e, S[s - 1])) and any(claim_var(k) == v and k[2] >= s for k in keys):
                sup.add(s)
                break
    return sup


def ancestor_closure(story: Story, ev: Event, keys: Sequence[Key]) -> Set[int]:
    """Secondary depth notion: transitive closure of support events through the reads of each supporting event."""
    W, S = tracer(story)
    byslot = {e.slot: e for e in story.events}
    sup, todo = set(), list(support_set(story, ev, keys))
    while todo:
        s = todo.pop()
        if s in sup:
            continue
        sup.add(s)
        for v in reads_of(byslot[s], story):
            w = W[s - 1].get(v, 0)
            if w:
                todo.append(w)
    return sup


# ----------------------------------------------------------------------------- label-independent claim-set rule
def core_keys(story: Story, ev: Event) -> List[Key]:
    d, H, a, p = ev.slot, story.horizon, ev.actor, ev.prop
    k = ev.kind
    if k == "move":
        c = [("loc", a, d - 1), ("loc", a, d), ("loc", a, H), ("injured", a, d - 1)]
        for q in story.props:
            c += [("proploc", q, d), ("holder", q, d - 1)]
    elif k == "give":
        c = [("holder", p, d - 1), ("holder", p, d), ("holder", p, H), ("loc", a, d - 1), ("loc", ev.target, d - 1), ("proploc", p, d)]
    elif k == "pickup":
        c = [("holder", p, d - 1), ("holder", p, d), ("proploc", p, d - 1), ("loc", a, d - 1), ("holder", p, H)]
    elif k == "drop":
        c = [("holder", p, d - 1), ("holder", p, d), ("proploc", p, d), ("loc", a, d - 1), ("proploc", p, H)]
    else:
        c = [("injured", a, d - 1), ("injured", a, d), ("injured", a, H), ("loc", a, d)]
    out = []
    for x in c:
        if x not in out:
            out.append(x)
    return out


def claim_keys(story: Story, ev: Event, evidence_text: str) -> List[Key]:
    """10 claims: the core set for this evidence kind + distractors drawn uniformly from the remaining keys.
    Depends only on evidence text, entity lists, horizon and slot - never on the event trajectory - so it is identical across a matched pair."""
    core = core_keys(story, ev)[:M_CLAIMS]
    seed = hashlib.sha256((evidence_text + "|" + ",".join(story.chars + story.props + story.locs) + f"|{story.horizon}").encode()).hexdigest()
    rng = random.Random(seed)
    pool = [k for k in story.all_keys() if k not in core and k[2] >= 1]
    rng.shuffle(pool)
    keys = core + pool[: M_CLAIMS - len(core)]
    rng.shuffle(keys)
    return keys


# ----------------------------------------------------------------------------- gold (V1 oracles, both must agree)
def final_state(story: Story, ev: Event, keys: Sequence[Key]):
    """-> (prior values, final values, labels) per key. final = REVISE value if the oracle revises, else the prior value
    (a CONFLICT/blocked event is rejected: the story world is unchanged). Raises InvalidIntervention if the evidence has no unique gold."""
    ga, gb = oracle_a.gold(story, ev, list(keys)), oracle_b.gold(story, ev, list(keys))
    if ga != gb:
        raise InvalidIntervention("oracle disagreement")
    pa, pb = oracle_a.values(story, list(keys)), oracle_b.values(story, list(keys))
    if pa != pb:
        raise InvalidIntervention("oracle prior disagreement")
    final = {k: (ga[k][1] if ga[k][0] == "REVISE" else pa[k]) for k in keys}
    return pa, final, {k: ga[k][0] for k in keys}


def story_valid(story: Story) -> bool:
    try:
        _, viol = oracle_a.replay(story, story.events)
    except (InvalidIntervention, KeyError):
        return False
    return not viol
