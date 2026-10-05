"""Gold oracle A: forward replay with a mutable state dict.

Independent of oracle_b.py (no shared code except the data types in world.py).
Returns {claim_key: (label, new_value)}, label in KEEP / REVISE / CONFLICT.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .world import Assertion, Event, Evidence, InvalidIntervention, Key, NOBODY, Story


def _fresh(story: Story) -> dict:
    return {"loc": dict(story.init_loc), "holder": dict(story.init_holder),
            "proploc": {p: story.init_proploc.get(p, "") for p in story.props}, "inj": set(story.init_injured)}


def _copy(st: dict) -> dict:
    return {"loc": dict(st["loc"]), "holder": dict(st["holder"]), "proploc": dict(st["proploc"]), "inj": set(st["inj"])}


def _apply(st: dict, e: Event) -> Optional[Tuple[str, str]]:
    """Apply event in place. Returns None if valid, else (attr, entity) of the contradicted claim.
    Raises InvalidIntervention if the failure has no unique contradicted claim."""
    if e.kind == "move":
        if e.actor in st["inj"]:
            return ("injured", e.actor)
        st["loc"][e.actor] = e.target
        for p, h in st["holder"].items():
            if h == e.actor:
                st["proploc"][p] = e.target
    elif e.kind == "give":
        if st["holder"][e.prop] != e.actor:
            return ("holder", e.prop)
        if st["loc"][e.actor] != st["loc"][e.target]:
            raise InvalidIntervention("give across locations")
        st["holder"][e.prop] = e.target
    elif e.kind == "pickup":
        if st["holder"][e.prop] != NOBODY:
            return ("holder", e.prop)
        if st["proploc"][e.prop] != st["loc"][e.actor]:
            raise InvalidIntervention("pickup elsewhere")
        st["holder"][e.prop] = e.actor
    elif e.kind == "drop":
        if st["holder"][e.prop] != e.actor:
            return ("holder", e.prop)
        st["holder"][e.prop] = NOBODY
        st["proploc"][e.prop] = st["loc"][e.actor]
    elif e.kind == "injure":
        st["inj"].add(e.actor)
    elif e.kind == "heal":
        st["inj"].discard(e.actor)
    elif e.kind == "noop":
        pass
    else:
        raise ValueError(e.kind)
    return None


def replay(story: Story, events: List[Event]) -> Tuple[List[dict], List[Tuple[int, Tuple[str, str]]]]:
    """Snapshots for slots 0..horizon and the list of (slot, contradicted (attr, entity)) violations."""
    st = _fresh(story)
    by_slot = {e.slot: e for e in events}
    snaps, viol = [_copy(st)], []
    for s in range(1, story.horizon + 1):
        if s in by_slot:
            bad = _apply(st, by_slot[s])
            if bad:
                viol.append((s, bad))
        snaps.append(_copy(st))
    return snaps, viol


def _read(snap: dict, attr: str, ent: str) -> str:
    if attr == "loc":
        return snap["loc"][ent]
    if attr == "holder":
        return snap["holder"][ent]
    if attr == "proploc":
        return snap["proploc"][ent]
    if attr == "injured":
        return "injured" if ent in snap["inj"] else "unharmed"
    raise ValueError(attr)


def values(story: Story, keys: List[Key]) -> Dict[Key, str]:
    snaps, viol = replay(story, story.events)
    assert not viol, f"story itself is invalid: {viol}"
    return {k: _read(snaps[k[2]], k[0], k[1]) for k in keys}


def forced_conflict_key(story: Story, ev: Evidence) -> Optional[Key]:
    """If the evidence contradicts the prior state, the (unique) contradicted claim key; else None."""
    if isinstance(ev, Assertion):
        snaps, _ = replay(story, story.events)
        return (ev.attr, ev.entity, ev.slot) if _read(snaps[ev.slot], ev.attr, ev.entity) != ev.value else None
    if ev.slot < 2:
        raise InvalidIntervention("slot<2")
    snaps, viol = replay(story, story.events + [ev])
    own = [v for v in viol if v[0] == ev.slot]
    other = [v for v in viol if v[0] != ev.slot]
    if other:
        raise InvalidIntervention("breaks later events")
    return (own[0][1][0], own[0][1][1], ev.slot - 1) if own else None


def gold(story: Story, ev: Evidence, keys: List[Key]) -> Dict[Key, Tuple[str, str]]:
    ck = forced_conflict_key(story, ev)
    if ck is not None:
        return {k: (("CONFLICT", "") if k == ck else ("KEEP", "")) for k in keys}
    if isinstance(ev, Assertion):
        return {k: ("KEEP", "") for k in keys}
    before, _ = replay(story, story.events)
    after, _ = replay(story, story.events + [ev])
    out = {}
    for k in keys:
        b, a = _read(before[k[2]], k[0], k[1]), _read(after[k[2]], k[0], k[1])
        out[k] = ("REVISE", a) if a != b else ("KEEP", "")
    return out
